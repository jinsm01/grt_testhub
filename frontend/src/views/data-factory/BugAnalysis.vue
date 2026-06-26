<template>
  <div class="bug-analysis-container">
    <!-- ==================== 列表视图 ==================== -->
    <template v-if="viewMode === 'list'">
      <!-- 顶部筛选栏 -->
      <div class="filter-bar">
        <el-input
          v-model="searchQuery"
          placeholder="搜索文件名"
          clearable
          @clear="handleSearch"
          @keyup.enter="handleSearch"
          style="width: 300px;"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <div class="filter-bar-spacer"></div>
        <!-- 文件选择输入框 -->
        <input
          ref="fileInput"
          type="file"
          accept=".xlsx,.xls"
          @change="onFileSelected"
          class="hidden-input"
          style="display: none;"
        />
        <!-- 未选择文件时显示选择按钮 -->
        <template v-if="!selectedFile">
          <el-button
            v-if="false"
            type="primary"
            class="select-file-btn"
            @click="triggerFileSelect"
            :disabled="analyzing"
          >
            <el-icon><FolderOpened /></el-icon>
            选择文件
          </el-button>
          <el-button
            type="success"
            class="yunxiao-sync-btn"
            @click="showYunxiaoDialog = true"
            :disabled="analyzing"
            style="margin-left: 4px;"
          >
            <el-icon style="margin-right: 4px;"><Refresh /></el-icon>
            云效同步
          </el-button>
        </template>
        <!-- 选择文件后显示文件信息和操作 -->
        <div v-else v-if="false" class="selected-file-info">
          <span
            class="file-name-text clickable"
            :title="selectedFile.name"
            @click="triggerFileSelect"
          >
            {{ selectedFile.name }}
          </span>
          <el-button
            type="primary"
            size="small"
            :loading="analyzing"
            :disabled="analyzing"
            @click="startAnalysis"
          >
            {{ analyzing ? '分析中' : '开始分析' }}
          </el-button>
        </div>
      </div>

      <!-- 历史记录列表 -->
      <div class="card-container history-card">
        <el-table
          ref="tableRef"
          v-loading="loadingHistory"
          :data="historyRecords"
          stripe
          style="width: 100%"
        >
          <el-table-column label="序号" width="80" header-align="center" align="center">
            <template #default="{ $index }">
              {{ $index + 1 }}
            </template>
          </el-table-column>

          <el-table-column label="文件名" min-width="280" show-overflow-tooltip header-align="center" align="left">
            <template #default="{ row }">
              <span class="file-name">{{ row.display_name || row.file_name || '未命名' }}</span>
            </template>
          </el-table-column>

          <el-table-column label="Bug 数量" width="120" header-align="center" align="center">
            <template #default="{ row }">
              <span class="count-badge">{{ row.total_bugs || 0 }}</span>
            </template>
          </el-table-column>

          <el-table-column v-if="false" label="P0 风险" width="110" header-align="center" align="center">
            <template #default="{ row }">
              <span
                class="p0-badge"
                :class="{ 'p0-badge-zero': !(row.meta_data?.p0_count > 0) }"
              >
                {{ row.meta_data?.p0_count || 0 }}
              </span>
            </template>
          </el-table-column>



          <el-table-column label="同步人" width="120" header-align="center" align="center">
            <template #default="{ row }">
              <span class="creator-text">{{ row.created_by || '-' }}</span>
            </template>
          </el-table-column>

          <el-table-column label="同步时间" width="200" header-align="center" align="center">
            <template #default="{ row }">
              <span class="time-text">{{ formatDateTime(row.created_at) }}</span>
            </template>
          </el-table-column>

          <el-table-column label="操作" width="300" fixed="right" header-align="center" align="center">
            <template #default="{ row }">
              <div class="action-buttons">
                <el-button size="small" type="primary" @click="viewAnalysisDetail(row)">
                  <el-icon><View /></el-icon>
                  <span>查看</span>
                </el-button>
                <el-button
                  v-if="row.source_type === 'yunxiao_api' || row.total_bugs > 0"
                  size="small"
                  type="info"
                  @click="openSyncLog(row)"
                >
                  <el-icon><Document /></el-icon>
                  <span>{{ row.source_type === 'yunxiao_api' ? '日志' : '原始数据' }}</span>
                </el-button>
                <el-button size="small" type="danger" @click="handleDeleteRecord(row)">
                  <el-icon><Delete /></el-icon>
                  <span>删除</span>
                </el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>

        <!-- 分页 -->
        <div class="pagination-container" v-if="!loadingHistory && historyRecords.length > 0">
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

        <!-- 空状态 -->
        <el-empty v-if="!loadingHistory && historyRecords.length === 0" description="暂无分析记录">
          <el-button v-if="false" type="primary" @click="showUploadDialog = true">
            <el-icon><Upload /></el-icon>
            上传文件开始分析
          </el-button>
        </el-empty>
      </div>
    </template>

    <!-- ==================== 分析结果详情视图 ==================== -->
    <template v-else-if="viewMode === 'detail'">
      <!-- 页面标题（临时隐藏，后续可能重新启用） -->
      <div v-show="showDetailHeader" class="detail-header">
        <div class="detail-header-left">
          <!-- 返回列表按钮已隐藏 -->
          <div class="detail-title">
            <h2>{{ currentRecord?.file_name || 'Bug 分析报告' }}</h2>
            <el-tag v-if="currentRecord?.version_tag" size="small" type="info">{{ currentRecord.version_tag }}</el-tag>
          </div>
        </div>
        <div class="detail-header-actions">
          <!-- 重新上传按钮已隐藏 -->
          <el-button type="primary" @click="showExportDialog = true">
            <el-icon><Download /></el-icon>
            导出报告
          </el-button>
        </div>
      </div>

      <!-- AI 分析状态提示 - 现代风格 -->
      <div v-if="aiStatus === 'pending' || aiStatus === 'running'" class="ai-progress-banner">
        <div class="ai-banner-content">
          <div class="ai-banner-icon">
            <el-icon class="ai-pulse-icon"><MagicStick /></el-icon>
          </div>
          <div class="ai-banner-text">
            <div class="ai-banner-title">AI 智能分析进行中</div>
            <div class="ai-banner-desc">基础数据已展示，正在生成关键词词频、回归风险等深度分析...</div>
          </div>
          <div class="ai-banner-progress">
            <div class="ai-progress-ring">
              <span class="ai-progress-value">{{ aiProgress }}%</span>
            </div>
          </div>
        </div>
        <div class="ai-progress-bar">
          <div class="ai-progress-fill" :style="{ width: `${aiProgress}%` }"></div>
        </div>
      </div>

      <!-- AI 分析失败提示 -->
      <el-alert
        v-if="aiStatus === 'failed'"
        title="AI 分析失败"
        type="error"
        :closable="false"
        show-icon
        style="margin-bottom: 16px;"
      >
        <template #default>
          <span>AI 分析过程中出现异常，请尝试重新同步或联系管理员。</span>
        </template>
      </el-alert>

      <!-- 分析结果内容 -->
      <!-- 操作栏已隐藏 - 功能合并到顶部导航栏 -->

      <!-- 历史记录侧栏 (V2新增) -->
      <transition name="slide-fade">
        <div v-if="showHistory" class="history-sidebar">
          <div class="history-header">
            <span class="history-title"><el-icon><Clock /></el-icon> 分析历史</span>
            <el-button text @click="showHistory = false"><el-icon><Close /></el-icon></el-button>
          </div>
          <div class="history-list" v-loading="loadingHistory">
            <div v-for="rec in historyRecords" :key="rec.id" class="history-item" :class="{ active: rec.id === currentRecordId }" @click="loadHistoryRecord(rec)">
              <div class="history-item-main">
                <span class="history-item-name">{{ rec.file_name || rec.version_tag || `#${rec.id}` }}</span>
                <el-tag size="small" :type="rec.meta_data?.p0_count > 0 ? 'danger' : 'info'" v-if="rec.meta_data">P0:{{ rec.meta_data.p0_count }}</el-tag>
              </div>
              <div class="history-item-meta">
                <span>{{ rec.total_bugs }}条</span><span>{{ rec.created_at }}</span>
                <span class="top-mod">{{ rec.meta_data?.top_module || '' }}</span>
              </div>
            </div>
            <el-empty v-if="!loadingHistory && historyRecords.length === 0" description="暂无迭代报告" :image-size="60" />
          </div>
        </div>
      </transition>

      <!-- 主内容区 -->
      <div class="main-content" :class="{ 'with-sidebar': showHistory }">

        <!-- 汇总统计卡片 -->
        <div class="summary-cards">
          <el-row :gutter="16">
            <el-col :span="6">
              <div class="summary-card">
                <div class="summary-icon" style="background: #fff5f7; color: #f8b4b4;"><el-icon><Document /></el-icon></div>
                <div class="summary-info">
                  <div class="summary-value">{{ defectCount }}</div>
                  <div class="summary-label">缺陷</div>
                  <div class="summary-sub">功能缺陷/体验问题</div>
                </div>
                <el-tooltip content="测试期间发现的各类功能缺陷和体验问题数量" placement="top" effect="dark">
                  <div class="card-tooltip-icon"><el-icon><InfoFilled /></el-icon></div>
                </el-tooltip>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="summary-card">
                <div class="summary-icon" style="background: #fff5f7; color: #f8b4b4;"><el-icon><Warning /></el-icon></div>
                <div class="summary-info">
                  <div class="summary-value">{{ onlineBugCount }}</div>
                  <div class="summary-label">线上故障</div>
                  <div class="summary-sub">生产环境问题</div>
                </div>
                <el-tooltip content="已发布到生产环境后发现的 Bug 数量，代表漏测风险" placement="top" effect="dark">
                  <div class="card-tooltip-icon"><el-icon><InfoFilled /></el-icon></div>
                </el-tooltip>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="summary-card">
                <div class="summary-icon" style="background: #f0f7ff; color: #a8d8ea;"><el-icon><Grid /></el-icon></div>
                <div class="summary-info">
                  <div class="summary-value">{{ Object.keys(modulesData).length }}</div>
                  <div class="summary-label">功能模块</div>
                  <div class="summary-sub">{{ (metaData && metaData.tag_count) || 0 }} 种标签归类</div>
                </div>
                <el-tooltip content="出现 Bug 的功能模块数量，反映问题分布的广度" placement="top" effect="dark">
                  <div class="card-tooltip-icon"><el-icon><InfoFilled /></el-icon></div>
                </el-tooltip>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="summary-card">
                <div class="summary-icon" style="background: #f0fff7; color: #a8e6cf;"><el-icon><TrendCharts /></el-icon></div>
                <div class="summary-info">
                  <div class="summary-value">{{ clusterData.length }}</div>
                  <div class="summary-label">缺陷聚集点</div>
                  <div class="summary-sub">>=5条的功能聚簇</div>
                </div>
                <el-tooltip content="Bug 数量>=5条的高密度功能模块数量，代表重点回归区域" placement="top" effect="dark">
                  <div class="card-tooltip-icon"><el-icon><InfoFilled /></el-icon></div>
                </el-tooltip>
              </div>
            </el-col>
          </el-row>
        </div>

        <!-- Tab 标签页导航 -->
        <div class="tab-navigation">
          <div 
            class="tab-item" 
            :class="{ active: activeTab === 'overview' }"
            @click="activeTab = 'overview'"
          >
            <el-icon><InfoFilled /></el-icon>
            <span>分析概览</span>
            <el-tag v-if="riskData && riskData.P0 && riskData.P0.total > 0" type="danger" size="small" class="tab-badge">P0</el-tag>
          </div>
          <div 
            class="tab-item" 
            :class="{ active: activeTab === 'charts' }"
            @click="activeTab = 'charts'"
          >
            <el-icon><Histogram /></el-icon>
            <span>图表分析</span>
            <el-tag type="info" size="small" class="tab-badge">{{ Object.keys(modulesData).length }}</el-tag>
          </div>
          <div 
            class="tab-item" 
            :class="{ active: activeTab === 'risk' }"
            @click="activeTab = 'risk'"
          >
            <el-icon><Warning /></el-icon>
            <span>回归风险</span>
            <el-tag v-if="riskData && (riskData.P0.total + riskData.P1.total + riskData.P2.total) > 0" 
                    :type="riskData.P0.total > 0 ? 'danger' : 'warning'" 
                    size="small" 
                    class="tab-badge">
              {{ riskData.P0.total + riskData.P1.total + riskData.P2.total }}
            </el-tag>
          </div>
          <div 
            class="tab-item" 
            :class="{ active: activeTab === 'focus' }"
            @click="activeTab = 'focus'"
          >
            <el-icon><List /></el-icon>
            <span>模块测试重点</span>
            <el-tag type="info" size="small" class="tab-badge">{{ Object.keys(testFocusData).length }}</el-tag>
          </div>
        </div>

        <!-- Tab 内容区域 -->
        <div class="tab-content">
          <!-- 概览 Tab -->
          <div v-show="activeTab === 'overview'" class="tab-panel">
            <!-- AI 加载骨架 - 无外层卡片，与回归风险保持一致 -->
            <div v-if="aiLoading && !aiSummary" class="ai-loading-container">
              <div class="ai-loading-header">
                <div class="ai-loading-pulse">
                  <el-icon class="is-loading"><Loading /></el-icon>
                </div>
                <div class="ai-loading-info">
                  <div class="ai-loading-title">AI 正在分析数据...</div>
                  <div class="ai-loading-desc">{{ aiLoadingText }}</div>
                </div>
              </div>
              <div class="ai-skeleton">
                <div class="ai-skeleton-line"></div>
                <div class="ai-skeleton-line"></div>
                <div class="ai-skeleton-line"></div>
              </div>
            </div>

            <!-- AI 总结摘要 (V2新增) - 只在有结果时显示 -->
            <el-card class="section-card collapsible-card" v-else-if="aiSummary">
              <template #header>
                <div class="card-header collapsible-header" @click="toggleSection('aiSummary')">
                  <span class="header-title"><el-icon><MagicStick /></el-icon> AI 智能摘要</span>
                  <div class="header-right">
                    <el-tag type="success" size="small" effect="dark" class="ai-status-tag success">
                      AI 已生成
                    </el-tag>
                    <el-icon class="collapse-icon" :class="{ 'is-collapsed': sectionCollapsed.aiSummary }">
                      <ArrowDown />
                    </el-icon>
                  </div>
                </div>
              </template>
              <div v-show="!sectionCollapsed.aiSummary" class="collapsible-content">
                <div class="ai-summary-content" v-html="formatAiSummary(aiSummary)"></div>
              </div>
            </el-card>
          </div>

          <!-- 图表 Tab -->
          <div v-show="activeTab === 'charts'" class="tab-panel">
            <!-- 模块分布图表 -->
            <el-row :gutter="16" class="chart-row">
              <el-col :span="24">
                <el-card class="chart-card">
                  <template #header>
                    <div class="chart-header-flex">
                      <span class="chart-title">模块分布</span>
                      <el-text type="info" size="small">(点击柱状图可定位到测试重点卡片对应模块)</el-text>
                    </div>
                  </template>
                  <div ref="moduleChartRef" class="chart-container clickable-chart" @click="onModuleChartClick"></div>
                  <!-- 未归类提示已移除，所有内容都在柱状图中显示 -->
                </el-card>
              </el-col>
            </el-row>

            <!-- 严重度交叉分析 -->
            <el-row :gutter="16" class="chart-row">
              <el-col :span="12">
                <el-card class="chart-card"><template #header><span class="chart-title">原始严重度 → 推断严重度 交叉对照</span></template>
                  <div ref="severityCrossChartRef" class="chart-container"></div>
                </el-card>
              </el-col>
              <el-col :span="12">
                <el-card class="chart-card"><template #header><span class="chart-title">推断严重度分布</span></template>
                  <div ref="severityPieChartRef" class="chart-container"></div>
                </el-card>
              </el-col>
            </el-row>

            <!-- 状态与优先级 -->
            <el-row :gutter="16" class="chart-row">
              <el-col :span="12">
                <el-card class="chart-card"><template #header><span class="chart-title">Bug 状态分布</span></template>
                  <div ref="statusChartRef" class="chart-container"></div>
                </el-card>
              </el-col>
              <el-col :span="12">
                <el-card class="chart-card"><template #header><span class="chart-title">优先级分布</span></template>
                  <div ref="priorityChartRef" class="chart-container"></div>
                </el-card>
              </el-col>
            </el-row>

            <!-- 关键词词频 -->
            <el-row :gutter="16" class="chart-row">
              <el-col :span="24">
                <el-card class="chart-card"><template #header><span class="chart-title">关键词词频 Top 20</span></template>
                  <div ref="keywordChartRef" class="chart-container"></div>
                </el-card>
              </el-col>
            </el-row>

            <!-- 创建者分布 -->
            <el-row :gutter="16" class="chart-row">
              <el-col :span="24">
                <el-card class="chart-card"><template #header><span class="chart-title">创建者 × 模块分布</span></template>
                  <div ref="creatorChartRef" class="chart-container" style="height: 400px;"></div>
                </el-card>
              </el-col>
            </el-row>

            <!-- 参与者分布 -->
            <el-row :gutter="16" class="chart-row" v-if="participantData.length > 0">
              <el-col :span="24">
                <el-card class="chart-card"><template #header><span class="chart-title">参与者 × 模块分布</span></template>
                  <div ref="participantChartRef" class="chart-container" style="height: 400px;"></div>
                </el-card>
              </el-col>
            </el-row>

            <!-- 其他自定义字段分布 -->
            <el-row v-for="(data, fieldName) in customFieldCharts" :key="fieldName" :gutter="16" class="chart-row">
              <el-col :span="24">
                <el-card class="chart-card">
                  <template #header><span class="chart-title">{{ fieldName }}分布（自定义字段）</span></template>
                  <div :ref="el => setCustomFieldChartRef(el, fieldName)" class="chart-container" style="height: 350px;"></div>
                </el-card>
              </el-col>
            </el-row>

            <!-- 时间趋势 -->
            <el-row :gutter="16" class="chart-row">
              <el-col :span="24">
                <el-card class="chart-card">
                  <template #header>
                    <span class="chart-title">Bug 创建时间趋势
                      <el-tag v-if="metaData && metaData.import_count > 0" size="small" type="info">已排除 {{ metaData.import_count }} 条平台导入数据</el-tag>
                    </span>
                  </template>
                  <div ref="timelineChartRef" class="chart-container" style="height: 300px;"></div>
                </el-card>
              </el-col>
            </el-row>
          </div>

          <!-- 风险 Tab -->
          <div v-show="activeTab === 'risk'" class="tab-panel">
            <!-- AI 加载状态 -->
            <div v-if="aiLoading" class="ai-risk-loading">
              <div class="ai-loading-header">
                <div class="ai-loading-pulse">
                  <el-icon class="is-loading"><Loading /></el-icon>
                </div>
                <div class="ai-loading-info">
                  <div class="ai-loading-title">AI 正在分析回归风险...</div>
                  <div class="ai-loading-desc">识别高风险场景、生成回归策略建议</div>
                </div>
              </div>
              <div class="ai-skeleton">
                <div class="ai-skeleton-line"></div>
                <div class="ai-skeleton-line"></div>
                <div class="ai-skeleton-line"></div>
              </div>
            </div>
            
            <!-- AI 风险分析结果 -->
            <div v-else-if="aiRisks && (aiRisks.P0?.length > 0 || aiRisks.P1?.length > 0 || aiRisks.P2?.length > 0)" class="ai-risk-result">
              <!-- P0 高风险 -->
              <div class="ai-risk-level-block p0-block" v-if="aiRisks.P0 && aiRisks.P0.length > 0">
                <div class="risk-level-header">
                  <div class="risk-level-icon">
                    <el-icon><WarningFilled /></el-icon>
                  </div>
                  <div class="risk-level-title">
                    <span class="level-name">P0 高风险</span>
                    <span class="level-desc">必须回归 · 服务中断/应用崩溃</span>
                  </div>
                  <div class="risk-level-count">
                    <span class="count-num">{{ aiRisks.P0.length }}</span>
                    <span class="count-label">类风险</span>
                  </div>
                </div>
                <div class="risk-items-grid">
                  <div v-for="(risk, idx) in aiRisks.P0" :key="idx" class="risk-item-card p0-item">
                    <div class="risk-item-content">
                      <span class="risk-type">{{ getRiskType(risk.description) }}</span>
                      <span class="risk-desc">{{ getRiskDesc(risk.description) }}</span>
                    </div>
                  </div>
                </div>
              </div>
              
              <!-- P1 中风险 -->
              <div class="ai-risk-level-block p1-block" v-if="aiRisks.P1 && aiRisks.P1.length > 0">
                <div class="risk-level-header">
                  <div class="risk-level-icon">
                    <el-icon><InfoFilled /></el-icon>
                  </div>
                  <div class="risk-level-title">
                    <span class="level-name">P1 中风险</span>
                    <span class="level-desc">应该回归 · 功能阻塞/修复质量存疑</span>
                  </div>
                  <div class="risk-level-count">
                    <span class="count-num">{{ aiRisks.P1.length }}</span>
                    <span class="count-label">类风险</span>
                  </div>
                </div>
                <div class="risk-items-grid">
                  <div v-for="(risk, idx) in aiRisks.P1" :key="idx" class="risk-item-card p1-item">
                    <div class="risk-item-content">
                      <span class="risk-type">{{ getRiskType(risk.description) }}</span>
                      <span class="risk-desc">{{ getRiskDesc(risk.description) }}</span>
                    </div>
                  </div>
                </div>
              </div>
              
              <!-- P2 低风险 -->
              <div class="ai-risk-level-block p2-block" v-if="aiRisks.P2 && aiRisks.P2.length > 0">
                <div class="risk-level-header">
                  <div class="risk-level-icon">
                    <el-icon><CircleCheck /></el-icon>
                  </div>
                  <div class="risk-level-title">
                    <span class="level-name">P2 低风险</span>
                    <span class="level-desc">按需回归 · 影响较轻/边界场景</span>
                  </div>
                  <div class="risk-level-count">
                    <span class="count-num">{{ aiRisks.P2.length }}</span>
                    <span class="count-label">类风险</span>
                  </div>
                </div>
                <div class="risk-items-grid">
                  <div v-for="(risk, idx) in aiRisks.P2" :key="idx" class="risk-item-card p2-item">
                    <div class="risk-item-content">
                      <span class="risk-type">{{ getRiskType(risk.description) }}</span>
                      <span class="risk-desc">{{ getRiskDesc(risk.description) }}</span>
                    </div>
                  </div>
                </div>
              </div>
              
            </div>
            
            <!-- 无AI结果时显示空状态 -->
            <el-empty v-else description="暂无 AI 风险分析结果" :image-size="80" />
          </div>

          <!-- 测试重点 Tab -->
          <div v-show="activeTab === 'focus'" class="tab-panel">
            <!-- 模块卡片网格 -->
            <div class="focus-cards-grid" v-if="Object.keys(testFocusData).length > 0">
              <div class="focus-card-wrapper" v-for="(info, module) in testFocusData" :key="module">
                <div :ref="el => setModuleCardRef(el, module)" 
                      :id="`module-card-${module}`"
                     class="focus-card" 
                     @click="handleCardClick($event, module)" 
                     :class="{ clickable: currentRecordId, highlighted: highlightedModule === module }">
                  <!-- AI分析结果展示 -->
                  <div v-if="aiModuleFocus[module]" class="ai-focus-card">
                    <div class="focus-header">
                      <span class="focus-name">{{ module }}</span>
                      <div class="focus-badges">
                        <el-tag v-if="aiModuleFocus[module].risk_level === 'high'" type="danger" size="small" effect="light">高风险</el-tag>
                        <el-tag v-else-if="aiModuleFocus[module].risk_level === 'medium'" type="warning" size="small" effect="light">中风险</el-tag>
                        <el-tag v-else type="success" size="small" effect="light">低风险</el-tag>
                        <el-tag type="info" size="small" effect="plain" style="margin-left: 4px;">{{ aiModuleFocus[module].total_count }}条</el-tag>
                      </div>
                    </div>
                    <div class="focus-body ai-body">
                      <!-- AI智能分析点 -->
                      <div class="ai-section-title">智能分析</div>
                      <div v-for="(point, idx) in aiModuleFocus[module].focus_points?.slice(0, 3)" :key="idx" 
                           class="ai-point-item" :class="point.level">
                        <div class="ai-point-type">
                          <el-tag :type="point.level==='high'?'danger':point.level==='medium'?'warning':'info'" size="small" effect="light">
                            {{ point.type }}
                          </el-tag>
                        </div>
                        <div class="ai-point-desc">{{ point.description }}</div>
                      </div>
                      <div v-if="aiModuleFocus[module].focus_points?.length > 3" class="more-points-hint">
                        +{{ aiModuleFocus[module].focus_points.length - 3 }} 更多...
                      </div>
                      <!-- 基础测试关注点 -->
                      <div class="base-section-title">基础关注点</div>
                      <ul class="focus-points base-focus-points">
                        <li v-for="(point, idx) in info.focus_points?.slice(0, 3)" :key="idx">{{ point }}</li>
                      </ul>
                      <div v-if="info.focus_points?.length > 3" class="more-points-hint">
                        +{{ info.focus_points.length - 3 }} 更多...
                      </div>
                    </div>
                  </div>
                  <!-- AI分析加载中 -->
                  <div v-else-if="moduleFocusLoading[module]" class="ai-loading-card">
                    <div class="focus-header">
                      <span class="focus-name">{{ module }}</span>
                      <el-tag v-if="currentAnalyzingModule === module" type="warning" size="small" effect="dark" class="analyzing-tag">
                        <el-icon class="is-loading"><Loading /></el-icon>
                        <span>分析中</span>
                      </el-tag>
                      <el-tag v-else type="info" size="small" class="queue-tag">排队中</el-tag>
                    </div>
                    <div class="ai-loading-body">
                      <el-skeleton :rows="2" animated />
                      <div class="ai-loading-text">
                        {{ currentAnalyzingModule === module ? 'AI分析中...' : '等待分析...' }}
                      </div>
                    </div>
                  </div>
                  <!-- 基础统计（降级显示）+ AI分析按钮 -->
                  <div v-else>
                    <div class="focus-header">
                      <span class="focus-name">{{ module }}</span>
                      <div class="focus-badges">
                        <el-tag v-if="info.online >= 20" type="danger" size="small">线上故障多({{ info.online }}条)</el-tag>
                        <el-tag v-else-if="info.online >= 5" type="warning" size="small">有线上故障({{ info.online }}条)</el-tag>
                        <el-tag v-if="info.reopened > 0" type="danger" size="small" style="margin-left: 8px;">二次回归({{ info.reopened }}条)</el-tag>
                      </div>
                    </div>
                    <div class="focus-body">
                      <div class="focus-stats"><span>总计: {{ info.total }} 条</span><span>Top缺陷: {{ info.top_types.map(t => t[0]).slice(0, 2).join(', ') }}</span></div>
                      <ul class="focus-points">
                        <li v-for="(point, idx) in info.focus_points" :key="idx" class="focus-point-item-with-icon">
                          <template v-if="parseFocusPoint(point).icon">
                            <el-icon :class="'focus-icon-' + parseFocusPoint(point).type" class="focus-point-icon">
                              <component :is="parseFocusPoint(point).icon" />
                            </el-icon>
                            <span class="focus-point-text">{{ parseFocusPoint(point).text }}</span>
                          </template>
                          <template v-else>{{ point }}</template>
                        </li>
                      </ul>
                      <!-- AI分析按钮 -->
                      <div class="ai-analyze-action" @click.stop @mousedown.stop @mouseup.stop>
                        <el-button
                          type="primary"
                          size="small"
                          :loading="currentAnalyzingModule === module"
                          :disabled="(currentAnalyzingModule && currentAnalyzingModule !== module) || analyzeQueue.includes(module)"
                          @click.stop="analyzeSingleModule(module)"
                        >
                          <el-icon><MagicStick /></el-icon>
                          {{ analyzeQueue.includes(module) ? '排队中' : 'AI智能分析' }}
                        </el-button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div><!-- end tab-content -->
      </div><!-- end main-content -->

      <!-- ===== 模块详情抽屉 (V2新增) ===== -->
      <el-drawer v-model="moduleDrawerVisible" :title="'模块详情: ' + selectedModule" direction="rtl" size="50%" destroy-on-close>
        <template #header>
          <div class="drawer-header">
            <span>{{ selectedModule }}</span>
            <el-space>
              <el-tag v-if="selectedModuleStats.online > 0" type="danger" size="small">线上故障 {{ selectedModuleStats.online }}</el-tag>
              <el-tag v-if="selectedModuleStats.reopened > 0" type="warning" size="small">二次打开 {{ selectedModuleStats.reopened }}</el-tag>
            </el-space>
          </div>
        </template>
        <div v-loading="loadingModuleDetail">
          <el-descriptions :column="3" border size="small" class="module-stats-desc">
            <el-descriptions-item label="总Bug数">{{ selectedModuleStats.total || '-' }}</el-descriptions-item>
            <el-descriptions-item label="线上故障">{{ selectedModuleStats.online || 0 }}</el-descriptions-item>
            <el-descriptions-item label="二次打开">{{ selectedModuleStats.reopened || 0 }}</el-descriptions-item>
          </el-descriptions>
          <!-- 缺陷类型分布 -->
          <div class="detail-section" v-if="selectedModuleStats.dtype_dist">
            <h4 class="detail-section-title">缺陷类型分布</h4>
            <div class="dtype-tags"><el-tag v-for="(count, dtype) in selectedModuleStats.dtype_dist" :key="dtype" :type="dtypeTagType(dtype)" effect="plain" round style="margin: 4px;">{{ dtype }} ({{ count }})</el-tag></div>
          </div>
          <!-- 智能模块测试重点 (三层架构) -->
          <div class="detail-section ai-section intelligent-focus" v-if="aiModuleFocus[selectedModule]||moduleFocusLoading[selectedModule]">
            <h4 class="detail-section-title ai-title">
              <el-icon><MagicStick /></el-icon> 智能测试重点
              <el-tag v-if="aiModuleFocus[selectedModule]?.risk_level==='high'" type="danger" size="small" effect="light" style="margin-left: 8px;">高风险</el-tag>
              <el-tag v-else-if="aiModuleFocus[selectedModule]?.risk_level==='medium'" type="warning" size="small" effect="light" style="margin-left: 8px;">中风险</el-tag>
              <el-tag v-else-if="aiModuleFocus[selectedModule]?.risk_level==='low'" type="success" size="small" effect="light" style="margin-left: 8px;">低风险</el-tag>
              <el-tag v-if="aiModuleFocus[selectedModule]?.cached" type="info" size="small" effect="plain" style="margin-left: 8px;">缓存</el-tag>
            </h4>
            <div v-loading="moduleFocusLoading[selectedModule]" class="intelligent-focus-content">
              <div v-if="aiModuleFocus[selectedModule]" class="focus-points-intelligent">
                <div v-for="(point, idx) in aiModuleFocus[selectedModule].focus_points" :key="idx" 
                     class="focus-point-item" :class="point.level">
                  <div class="point-header">
                    <el-tag :type="point.level==='high'?'danger':point.level==='medium'?'warning':'info'" size="small" effect="light">
                      {{ point.type }}
                    </el-tag>
                    <span v-if="point.source==='layer1'" class="point-source">统计</span>
                    <span v-else-if="point.source==='layer2'" class="point-source ai">AI洞察</span>
                    <span v-else-if="point.source==='layer3'" class="point-source">关联</span>
                  </div>
                  <div class="point-desc">{{ point.description }}</div>
                  <div class="point-suggestion" v-if="point.test_suggestion">
                    <el-icon><Check /></el-icon> {{ point.test_suggestion }}
                  </div>
                  <div class="point-root-cause" v-if="point.root_cause">
                    <el-text type="info" size="small">根因: {{ point.root_cause }}</el-text>
                  </div>
                </div>
              </div>
              <div v-else class="focus-loading-hint">AI 正在分析模块特征...</div>
            </div>
            <!-- 技术洞察 -->
            <div v-if="aiModuleFocus[selectedModule]?.layer2_insights?.technical_insights" class="technical-insights">
              <el-divider content-position="left">技术洞察</el-divider>
              <el-descriptions :column="1" size="small" border>
                <el-descriptions-item label="主要问题域">{{ aiModuleFocus[selectedModule].layer2_insights.technical_insights.primary_domain }}</el-descriptions-item>
                <el-descriptions-item label="架构关注点" v-if="aiModuleFocus[selectedModule].layer2_insights.technical_insights.architecture_concern">
                  {{ aiModuleFocus[selectedModule].layer2_insights.technical_insights.architecture_concern }}
                </el-descriptions-item>
              </el-descriptions>
            </div>
          </div>
          <!-- AI 测试建议 (旧版兼容) -->
          <div class="detail-section ai-section" v-if="getAiTestFocus(selectedModule)">
            <h4 class="detail-section-title ai-title"><el-icon><MagicStick /></el-icon> AI 测试建议</h4>
            <div class="ai-content" v-html="formatAiFocus(getAiTestFocus(selectedModule))"></div>
          </div>
          <!-- AI 根因假设 -->
          <div class="detail-section ai-section" v-if="getAiRootCause(selectedModule)">
            <h4 class="detail-section-title ai-title"><el-icon><Search /></el-icon> AI 根因假设</h4>
            <div class="ai-content cause-content">{{ getAiRootCause(selectedModule) }}</div>
          </div>
          <!-- 基础测试关注点 -->
          <div class="detail-section" v-if="selectedModuleStats.focus_points">
            <h4 class="detail-section-title">基础测试关注点</h4>
            <ul class="focus-points-list">
              <li v-for="(point, idx) in selectedModuleStats.focus_points" :key="idx" class="focus-point-item-with-icon">
                <template v-if="parseFocusPoint(point).icon">
                  <el-icon :class="'focus-icon-' + parseFocusPoint(point).type" class="focus-point-icon">
                    <component :is="parseFocusPoint(point).icon" />
                  </el-icon>
                  <span class="focus-point-text">{{ parseFocusPoint(point).text }}</span>
                </template>
                <template v-else>{{ point }}</template>
              </li>
            </ul>
          </div>
          <!-- Bug 明细表格 -->
          <div class="detail-section bug-list-section">
            <h4 class="detail-section-title">Bug 明细列表 <el-text type="info" size="small">({{ filteredModuleBugs.length }} 条)</el-text></h4>
            <div class="bug-filter-bar">
              <el-input v-model="bugFilter.keyword" placeholder="搜索标题..." clearable size="small" style="width: 200px;" prefix-icon="Search" />
              <el-select v-model="bugFilter.severity" placeholder="严重度" clearable size="small" style="width: 130px;"><el-option label="P0" value="P0"/><el-option label="P1" value="P1"/><el-option label="P2" value="P2"/></el-select>
              <el-select v-model="bugFilter.defectType" placeholder="缺陷类型" clearable size="small" style="width: 140px;"><el-option v-for="dt in Object.keys(selectedModuleStats.dtype_dist || {})" :key="dt" :label="dt" :value="dt"/></el-select>
            </div>
            <el-table :data="filteredModuleBugs" border size="small" max-height="400" stripe>
              <el-table-column prop="title" label="标题" min-width="220" show-overflow-tooltip />
              <el-table-column prop="inferred_sev" label="推断严重度" width="90" align="center"><template #default="{ row }"><el-tag :type="sevTagType(row.inferred_sev)" size="small">{{ row.inferred_sev }}</el-tag></template></el-table-column>
              <el-table-column prop="defect_type" label="缺陷类型" width="100" align="center" />
              <el-table-column prop="status" label="状态" width="90" align="center" />
              <el-table-column prop="creator" label="创建者" width="90" align="center" />
              <el-table-column prop="created" label="创建时间" width="120" align="center" sortable />
            </el-table>
          </div>
        </div>
      </el-drawer>

      <!-- ===== 状态Bug列表抽屉 ===== -->
      <el-drawer v-model="statusBugDrawerVisible" :title="`状态: ${selectedStatus} (${statusBugList.length}条)`" direction="rtl" size="50%" destroy-on-close>
        <div class="status-bug-list">
          <el-empty v-if="statusBugList.length === 0" description="暂无数据" />
          <div v-else class="bug-list-container">
            <div v-for="(bug, idx) in statusBugList" :key="idx" class="bug-list-item">
              <div class="bug-item-header">
                <span class="bug-serial" v-if="bug.serialNumber">{{ bug.serialNumber }}</span>
                <el-tag size="small" :type="sevTagType(bug.severity)" class="bug-sev-tag">{{ bug.severity || '未知' }}</el-tag>
                <span class="bug-title">{{ bug.title || '无标题' }}</span>
              </div>
              <div class="bug-item-meta">
                <span class="bug-creator">创建者: {{ bug.creator || '-' }}</span>
                <span class="bug-module">模块: {{ bug.module || '-' }}</span>
                <span class="bug-date">{{ bug.created || '-' }}</span>
              </div>
              <div v-if="bug.desc" class="bug-item-desc">{{ bug.desc }}</div>
            </div>
          </div>
        </div>
      </el-drawer>

      <!-- ===== 回归导出对话框 (V2新增) ===== -->
      <el-dialog v-model="showExportDialog" title="导出回归清单" width="560px" destroy-on-close>
        <div class="export-options">
          <el-form label-width="120px">
            <el-form-item label="导出格式:"><el-radio-group v-model="exportFormat"><el-radio value="markdown">Markdown</el-radio><el-radio value="excel">Excel</el-radio></el-radio-group></el-form-item>
            <el-form-item label="导出范围:"><el-radio-group v-model="exportScope"><el-radio value="all">全部模块</el-radio><el-radio value="top5">Top5 模块</el-radio><el-radio value="custom">自定义</el-radio></el-radio-group></el-form-item>
            <el-form-item v-if="exportScope === 'custom'" label="选择模块:">
              <el-select v-model="exportCustomModules" multiple collapse-tags placeholder="选择要导出的模块">
                <el-option v-for="(cnt, mod) in modulesData" :key="mod" :label="`${mod} (${cnt})`" :value="mod" />
              </el-select>
            </el-form-item>
          </el-form>
        </div>
        <template #footer>
          <el-button @click="showExportDialog = false">取消</el-button>
          <el-button class="export-confirm-btn" type="primary" @click="doExport" :loading="exporting">
            <el-icon><Download /></el-icon> 导出
          </el-button>
        </template>
      </el-dialog>

    </template>
    <!-- end detail view -->

    <!-- ==================== 上传对话框 ==================== -->
    <el-dialog v-model="showUploadDialog" title="上传 Bug 文件分析" width="600px" destroy-on-close>
      <el-upload
        class="upload-area"
        drag
        action="#"
        :auto-upload="false"
        :on-change="handleFileChange"
        :limit="1"
        accept=".xlsx,.xls"
        :disabled="analyzing"
      >
        <el-icon class="upload-icon" :class="{ 'is-loading': analyzing }">
          <component :is="analyzing ? 'Loading' : 'UploadFilled'" />
        </el-icon>
        <div class="upload-text">
          <p v-if="!analyzing">拖拽 Excel 文件到此处，或 <em>点击上传</em></p>
          <p v-else class="analyzing-text"><el-icon class="is-loading"><Loading /></el-icon>正在分析中，请稍候...</p>
          <p class="upload-tip">支持从云效导出的 .xlsx/.xls 格式 Bug 清单</p>
        </div>
      </el-upload>

      <!-- 版本标签配置 - 紫色调 -->
      <div class="version-config" style="margin-top: 24px; padding: 20px; background: linear-gradient(135deg, #f8f7ff 0%, #f5f3ff 100%); border-radius: 8px; border: 1px solid rgba(147,112,219,0.2);">
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
          <el-icon style="color: #7b42f6; font-size: 18px;"><InfoFilled /></el-icon>
          <span style="font-weight: 600; color: #5a32a3;">版本信息</span>
          <el-tag size="small" type="info" effect="plain" style="background: rgba(147,112,219,0.1); color: #7b42f6; border-color: rgba(147,112,219,0.3);">必填</el-tag>
        </div>
        <el-form label-width="0">
          <el-form-item style="margin-bottom: 0;">
            <el-input 
              v-model="versionTag" 
              placeholder="请输入版本标签，如：v6.0.0-release" 
              style="width: 100%;" 
              clearable
              :prefix-icon="Grid"
            >
              <template #append>
                <el-tooltip content="用于标识本次分析的版本/迭代，便于后续检索和对比" placement="top">
                  <el-icon style="color: #94a3b8;"><InfoFilled /></el-icon>
                </el-tooltip>
              </template>
            </el-input>
          </el-form-item>
        </el-form>
        <div style="margin-top: 12px; font-size: 12px; color: #7b42f6; display: flex; align-items: center; gap: 6px;">
          <el-icon style="font-size: 14px; color: #7b42f6;"><Clock /></el-icon>
          <span>分析记录将自动保存到迭代报告，可通过版本标签快速检索</span>
        </div>
      </div>

      <template #footer>
        <el-button @click="showUploadDialog = false">取消</el-button>
        <el-button type="primary" @click="startAnalysis" :loading="analyzing" :disabled="!fileName">
          开始分析
        </el-button>
      </template>
    </el-dialog>

    <!-- ==================== 云效同步抽屉 ==================== -->
    <el-drawer
      v-model="showYunxiaoDialog"
      title="云效同步Bug"
      direction="rtl"
      size="600px"
      :close-on-click-modal="false"
      destroy-on-close
      class="yunxiao-sync-drawer"
    >
      <div class="yunxiao-drawer-body">
        <el-form
          ref="yunxiaoFormRef"
          :model="yunxiaoForm"
          label-width="100px"
          :rules="yunxiaoRules"
          class="yunxiao-form"
        >
          <el-form-item label="访问令牌" prop="token">
            <el-input
              v-model="yunxiaoForm.token"
              type="password"
              show-password
              placeholder="云效个人访问令牌 (PAT)"
              clearable
            />
          </el-form-item>

          <el-form-item label="组织 ID" prop="organization_id">
            <el-input
              v-model="yunxiaoForm.organization_id"
              placeholder="组织管理后台获取"
              clearable
            />
          </el-form-item>

          <el-form-item label="项目" prop="space_id">
            <el-select
              v-model="yunxiaoForm.space_id"
              placeholder="选择项目"
              filterable
              clearable
              remote
              :remote-method="searchYunxiaoProjects"
              :loading="yunxiaoProjectLoading"
              style="width: 100%;"
              @change="onYunxiaoProjectChange"
            >
              <el-option
                v-for="proj in yunxiaoProjects"
                :key="proj.id"
                :label="proj.name"
                :value="proj.id"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="迭代" prop="sprint_id">
            <el-select
              v-model="yunxiaoForm.sprint_id"
              placeholder="选择迭代 (不选拉取全部)"
              filterable
              clearable
              :loading="yunxiaoSprintLoading"
              style="width: 100%;"
              :disabled="!yunxiaoForm.space_id"
            >
              <el-option
                v-for="sp in yunxiaoSprints"
                :key="sp.id"
                :label="sp.name"
                :value="sp.id"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="版本标签" prop="version_tag">
            <el-input
              v-model="yunxiaoForm.version_tag"
              placeholder="用于标识本次同步，如 v6.0.0-sprint5"
              clearable
            />
          </el-form-item>

          <el-form-item label="最大数量" prop="max_bugs">
            <div class="max-bugs-row">
              <el-input-number v-model="yunxiaoForm.max_bugs" :min="1" :max="2000" :step="100" />
              <span class="form-tip-inline">最多拉取条数</span>
            </div>
          </el-form-item>
        </el-form>
      </div>

      <template #footer>
        <div class="yunxiao-drawer-footer">
          <el-button @click="showYunxiaoDialog = false">取消</el-button>
          <el-button
            type="primary"
            @click="startYunxiaoSync"
            :loading="analyzing"
            :disabled="!yunxiaoForm.token || !yunxiaoForm.space_id"
          >
            开始同步
          </el-button>
        </div>
      </template>
    </el-drawer>

    <!-- 同步日志抽屉 -->
    <el-drawer
      v-model="showSyncLogDialog"
      title="云效同步日志详情"
      size="80%"
      direction="rtl"
      :close-on-click-modal="false"
      class="sync-log-drawer"
    >
      <div v-if="syncLogLoading" class="sync-log-loading">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span>加载同步日志...</span>
      </div>

      <div v-else-if="syncLogData" class="sync-log-content">
        <!-- 字段填充率统计 -->
        <el-card class="sync-log-card" shadow="never" style="margin-top: 12px;">
          <template #header>
            <span class="sync-log-title">字段填充率统计</span>
          </template>
          <el-table :data="Object.entries(syncLogData.field_stats || {}).map(([k, v]) => ({ field: k, ...v }))" stripe size="small" style="width: 100%">
            <el-table-column prop="field" label="字段名" min-width="200">
              <template #default="{ row }">
                {{ getFieldDisplayName(row.field) }}
              </template>
            </el-table-column>
            <el-table-column prop="filled" label="已填充" min-width="120" />
            <el-table-column prop="total" label="总数" min-width="120" />
            <el-table-column prop="rate" label="填充率" min-width="120">
              <template #default="{ row }">
                <el-tag :type="row.rate >= 90 ? 'success' : row.rate >= 50 ? 'warning' : 'danger'" size="small">
                  {{ row.rate }}%
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <!-- 原始字段名 + 自定义字段名 并排 -->
        <div class="sync-log-row" style="margin-top: 12px;">
          <!-- 云效原始字段名（用于诊断字段名匹配问题） -->
          <el-card class="sync-log-card" shadow="never">
            <template #header>
              <span class="sync-log-title">云效原始字段名 (_raw_yunxiao keys)</span>
              <el-tag type="warning" size="small" style="margin-left: 8px;">
                共 {{ (syncLogData.first_bug_raw_keys || []).length }} 个
              </el-tag>
            </template>
            <div class="custom-field-keys">
              <el-tag
                v-for="key in syncLogData.first_bug_raw_keys || []"
                :key="key"
                size="small"
                style="margin: 4px;"
                type="info"
                :title="key"
              >
                {{ getFieldDisplayName(key) }}
              </el-tag>
              <el-empty v-if="!(syncLogData.first_bug_raw_keys || []).length" description="无原始字段数据" :image-size="60" />
            </div>
          </el-card>

          <!-- 所有自定义字段名 -->
          <el-card class="sync-log-card" shadow="never">
            <template #header>
              <span class="sync-log-title">所有自定义字段名 (custom_fields)</span>
              <el-tag type="info" size="small" style="margin-left: 8px;">
                共 {{ (syncLogData.all_custom_field_keys || []).length }} 个字段
              </el-tag>
            </template>
            <div class="custom-field-keys">
              <el-tag
                v-for="key in syncLogData.all_custom_field_keys || []"
                :key="key"
                size="small"
                style="margin: 4px;"
                :type="['参与者', '参与人', '相关人员', '协同人', '参与人员', 'participant', 'participants'].includes(key) ? 'success' : 'info'"
              >
                {{ key }}
              </el-tag>
              <el-empty v-if="!(syncLogData.all_custom_field_keys || []).length" description="无自定义字段" :image-size="60" />
            </div>
          </el-card>
        </div>

        <!-- 前10条Bug样本 -->
        <el-card class="sync-log-card" shadow="never" style="margin-top: 12px;">
          <template #header>
            <span class="sync-log-title">前10条Bug样本</span>
          </template>
          <el-table :data="syncLogData.sample_bugs || []" stripe size="small" max-height="400">
            <el-table-column prop="index" label="#" width="50" />
            <el-table-column prop="serialNumber" label="编号" width="120" />
            <el-table-column prop="title" label="标题" min-width="150" show-overflow-tooltip />
            <el-table-column prop="created" label="创建时间" width="150" />
            <el-table-column prop="updated" label="更新时间" width="150" />
            <el-table-column prop="creator" label="创建者" width="100" />
            <el-table-column prop="status" label="状态" width="100" />
            <el-table-column prop="severity" label="严重度" width="100" />
            <el-table-column label="自定义字段" min-width="200">
              <template #default="{ row }">
                <div class="custom-fields-preview">
                  <el-tag
                    v-for="(value, key) in row.custom_fields || {}"
                    :key="key"
                    size="small"
                    style="margin: 2px;"
                    type="info"
                  >
                    {{ key }}: {{ Array.isArray(value) ? value.join(',') : value }}
                  </el-tag>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <!-- 第一条Bug完整字段 -->
        <el-card class="sync-log-card" shadow="never" style="margin-top: 12px;">
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span class="sync-log-title">第一条Bug完整字段信息</span>
              <el-button size="small" @click="copyFirstBugFields">
                <el-icon><Document /></el-icon>
                复制JSON
              </el-button>
            </div>
          </template>
          <pre class="first-bug-json">{{ JSON.stringify(syncLogData.first_bug_fields, null, 2) }}</pre>
        </el-card>
      </div>

      <template #footer>
        <el-button @click="showSyncLogDialog = false">关闭</el-button>
      </template>
    </el-drawer>
  </div><!-- end bug-analysis-container -->
</template>

<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as echarts from 'echarts'
import { DataAnalysis, UploadFilled, Loading, RefreshLeft, Document, Grid, TrendCharts, User,
  InfoFilled, Warning, List, Clock, Close, Download, MagicStick, Search, Check, View, Delete, ArrowLeft, Upload, CircleCheck, FolderOpened,
  CircleClose, Refresh, Flag, Lightning, AlarmClock, ArrowDown, Histogram } from '@element-plus/icons-vue'
import { analyzeBugExcel, enhanceWithAI, getBugAnalysisRecords, getBugAnalysisRecordDetail, getModuleDetail, deleteBugAnalysisRecord, analyzeModuleFocusIntelligent, getYunxiaoProjects, getYunxiaoSprints, syncFromYunxiao, getYunxiaoSyncLog, getBugAnalysisAiStatus } from '@/api/data-factory'

const route = useRoute()
const router = useRouter()

// ==================== 视图控制 ====================
const viewMode = ref(route.query.view === 'detail' ? 'detail' : 'list') // 'list' | 'detail'
const showUploadDialog = ref(false)
const searchQuery = ref('')

// ==================== 状态 ====================
const analyzing = ref(false)
const analysisResult = ref(false)
const fileName = ref('')
const currentRecordId = ref(null)
const currentRecord = ref(null)
const aiStatus = ref('none')  // none | pending | running | completed | failed
const aiProgress = ref(0)
let aiPollingTimer = null

// 文件上传相关
const fileInput = ref(null)
const selectedFile = ref(null)

// AI 配置 (V2)
const aiProvider = ref('qwen')
const versionTag = ref('')
const saveRecord = ref(true)

// AI 加载状态 (渐进式加载)
const aiLoading = ref(false)
const aiLoadingText = ref('AI 分析中...')

// 历史记录 (V2)
const historyRecords = ref([])
const loadingHistory = ref(false)
const tableRef = ref(null)
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)

// 模块详情 (V2)
const moduleDrawerVisible = ref(false)
const selectedModule = ref('')
const selectedModuleStats = ref({})
const moduleBugs = ref([])
const loadingModuleDetail = ref(false)
const bugFilter = ref({ keyword: '', severity: '', defectType: '' })
const bugPage = ref(1)

// 导出 (V2)
const showExportDialog = ref(false)
const exportFormat = ref('markdown')
const exportScope = ref('top5')

// 状态Bug列表抽屉
const statusBugDrawerVisible = ref(false)
const selectedStatus = ref('')
const statusBugList = ref([])
const exportCustomModules = ref([])
const exporting = ref(false)

// 云效同步
const showYunxiaoDialog = ref(false)
const yunxiaoFormRef = ref(null)
const yunxiaoForm = ref({
  token: '',
  organization_id: '',
  space_id: '',
  sprint_id: '',
  version_tag: '',
  max_bugs: 1000,
})
const yunxiaoRules = {
  token: [{ required: true, message: '请输入云效访问令牌', trigger: 'blur' }],
  space_id: [{ required: true, message: '请选择项目', trigger: 'change' }],
}
const yunxiaoProjects = ref([])
const yunxiaoSprints = ref([])
const yunxiaoProjectLoading = ref(false)
const yunxiaoSprintLoading = ref(false)

// 同步日志对话框
const showSyncLogDialog = ref(false)
const syncLogLoading = ref(false)
const syncLogData = ref(null)

// 字段名中文映射（标准化字段 + 云效原始字段）
const FIELD_NAME_MAP = {
  // 标准化字段
  title: '标题',
  created: '创建时间',
  updated: '更新时间',
  creator: '创建者',
  status: '状态',
  severity: '严重度',
  priority: '优先级',
  module: '模块',
  custom_fields: '自定义字段',
  // 云效原始字段
  id: 'ID',
  identifier: '标识',
  serialNumber: '编号',
  subject: '标题',
  name: '名称',
  description: '描述',
  content: '内容',
  severityName: '严重度名称',
  priorityName: '优先级名称',
  moduleName: '模块名称',
  assignedTo: '指派给',
  assignee: '处理人',
  reporter: '报告人',
  participants: '参与者',
  participant: '参与者',
  workitemType: '工作项类型',
  category: '分类',
  type: '类型',
  gmtCreate: '创建时间',
  gmt_create: '创建时间',
  createdAt: '创建时间',
  created_at: '创建时间',
  createTime: '创建时间',
  create_time: '创建时间',
  createdTime: '创建时间',
  created_time: '创建时间',
  gmtCreateTime: '创建时间',
  gmt_create_time: '创建时间',
  gmtModified: '修改时间',
  gmt_modified: '修改时间',
  modifiedAt: '修改时间',
  modified_at: '修改时间',
  updateTime: '更新时间',
  update_time: '更新时间',
  updatedTime: '更新时间',
  updated_time: '更新时间',
  gmtModifyTime: '修改时间',
  gmt_modify_time: '修改时间',
  gmtClosed: '关闭时间',
  gmt_closed: '关闭时间',
  closedAt: '关闭时间',
  closed_at: '关闭时间',
  closeTime: '关闭时间',
  close_time: '关闭时间',
  customFieldValues: '自定义字段值',
  customFieldValueList: '自定义字段值列表',
  customFields: '自定义字段',
  fieldValueMap: '字段值映射',
  extraFields: '额外字段',
  custom_field_values: '自定义字段值',
  spaceId: '空间ID',
  spaceType: '空间类型',
  sprint: '迭代',
  sprintId: '迭代ID',
  tags: '标签',
  tag: '标签',
  parent: '父项',
  parentId: '父项ID',
  children: '子项',
  attachments: '附件',
  attachment: '附件',
  comments: '评论',
  comment: '评论',
  watchers: '关注者',
  watcher: '关注者',
  followers: '关注者',
  follower: '关注者',
  solution: '解决方案',
  remark: '备注',
  desc: '描述',
}

function getFieldDisplayName(field) {
  return FIELD_NAME_MAP[field] || field
}

// 控制详情页头部显示（临时隐藏，后续可能重新启用）
const showDetailHeader = ref(false)

// 图表引用
const moduleChartRef = ref(null), severityCrossChartRef = ref(null), severityPieChartRef = ref(null)
const statusChartRef = ref(null), priorityChartRef = ref(null), keywordChartRef = ref(null)
const creatorChartRef = ref(null), timelineChartRef = ref(null), participantChartRef = ref(null)

// 数据
const modulesData = ref({}), featureDetailData = ref([]), severityCrossData = ref({})
const sevInfData = ref({}), sevData = ref({}), statusData = ref({}), priorityData = ref({})
const kwData = ref([]), timelineCleanData = ref({}), timelineData = ref({})
const creatorModuleData = ref([]), participantData = ref([]), customFieldCharts = ref({}), riskData = ref({ P0:{total:0,detail:{}}, P1:{total:0,detail:{}}, P2:{total:0,detail:{}} })
const clusterData = ref([]), rootCauseData = ref([]), testFocusData = ref({}), metaData = ref({})
const aiSummary = ref(''), aiTestFocus = ref({}), aiRootCause = ref([]), aiRisks = ref({}), aiKeywords = ref([])
const summaryLines = ref([]), actionLines = ref([])
const rawBugs = ref([])  // 原始Bug数据，用于状态筛选
// 智能模块分析结果 (三层架构)
const aiModuleFocus = ref({})
const moduleFocusLoading = ref({})

// 板块折叠展开状态
const sectionCollapsed = ref({
  aiSummary: false,      // AI智能摘要
  charts: false,         // 图表区域
  riskAnalysis: false,   // 回归风险分析
  testFocus: false       // 模块迭代测试重点
})

// Tab 标签页状态
const activeTab = ref('overview')  // overview | charts | risk | focus
const isAnalyzingAllModules = ref(false)
// 全局分析状态锁和队列
const currentAnalyzingModule = ref('')
const analyzeQueue = ref([])
const isProcessingQueue = ref(false)
const isAllModulesAnalyzed = computed(() => {
  const modules = Object.keys(testFocusData.value)
  if (modules.length === 0) return false
  return modules.every(m => aiModuleFocus.value[m])
})

// 模块卡片联动相关
const highlightedModule = ref('')
const moduleCardRefs = ref({})

// 设置模块卡片ref
const setModuleCardRef = (el, moduleName) => {
  if (el) {
    moduleCardRefs.value[moduleName] = el
  }
}

// 自定义字段图表引用
const customFieldChartRefs = ref({})
const customFieldChartInstances = ref({})

const setCustomFieldChartRef = (el, fieldName) => {
  if (el) {
    customFieldChartRefs.value[fieldName] = el
  }
}

let _rawAnalysisResult = null

// ==================== 计算属性 ================= ===
const workTypesText = computed(() => {
  const types = metaData.value?.work_types || {}
  return Object.entries(types).map(([k, v]) => `${k}${v}`).join('+') || '缺陷+线上故障'
})
// 缺陷数量
const defectCount = computed(() => {
  const types = metaData.value?.work_types || {}
  return types['缺陷'] || types['缺陷Bug'] || 0
})
// 线上故障数量
const onlineBugCount = computed(() => {
  const types = metaData.value?.work_types || {}
  return types['线上故障'] || types['线上'] || 0
})
const hasAiData = computed(() => !!aiSummary.value || Object.keys(aiTestFocus.value).length > 0)
const filteredModuleBugs = computed(() => {
  let list = moduleBugs.value
  if (bugFilter.value.keyword) {
    const kw = bugFilter.value.keyword.toLowerCase()
    list = list.filter(b => b.title.toLowerCase().includes(kw))
  }
  if (bugFilter.value.severity) list = list.filter(b => b.inferred_sev === bugFilter.value.severity)
  if (bugFilter.value.defectType) list = list.filter(b => b.defect_type === bugFilter.value.defectType)
  return list
})

const p0RiskData = computed(() => {
  // 只使用 AI 生成的风险类型，没有则返回空数组
  if (aiRisks.value?.P0?.length > 0) {
    const total = metaData.value?.total_bugs || 1
    return aiRisks.value.P0.map(item => ({
      ...item,
      percentage: item.percentage || `${((item.count || 0) / total * 100).toFixed(1)}%`
    }))
  }
  // AI分析完成前显示为空
  return []
})
const p1RiskData = computed(() => {
  // 只使用 AI 生成的风险类型，没有则返回空数组
  if (aiRisks.value?.P1?.length > 0) {
    const total = metaData.value?.total_bugs || 1
    return aiRisks.value.P1.map(item => ({
      ...item,
      percentage: item.percentage || `${((item.count || 0) / total * 100).toFixed(1)}%`
    }))
  }
  // AI分析完成前显示为空
  return []
})
const p2RiskData = computed(() => {
  // 只使用 AI 生成的风险类型，没有则返回空数组
  if (aiRisks.value?.P2?.length > 0) {
    const total = metaData.value?.total_bugs || 1
    return aiRisks.value.P2.map(item => ({
      ...item,
      percentage: item.percentage || `${((item.count || 0) / total * 100).toFixed(1)}%`
    }))
  }
  // AI分析完成前显示为空
  return []
})

// ==================== 工具方法 ====================
function getAiTestFocus(m) { return aiTestFocus.value[m] || '' }
function getAiRootCause(m) { return (aiRootCause.value.find(r=>r.module===m)||{}).cause||'' }

// 拆分风险描述：获取冒号前的部分（风险类型）
function getRiskType(desc) {
  if (!desc) return ''
  const colonIndex = desc.indexOf('：') || desc.indexOf(':')
  if (colonIndex > 0) {
    return desc.substring(0, colonIndex + 1)
  }
  return ''
}

// 拆分风险描述：获取冒号后的部分（具体内容）
function getRiskDesc(desc) {
  if (!desc) return ''
  const colonIndex = desc.indexOf('：') || desc.indexOf(':')
  if (colonIndex > 0) {
    return desc.substring(colonIndex + 1)
  }
  return desc
}

function sevTagType(sev){return{'P0':'danger','P1':'warning','P2':'info'}[sev]||''}
function dtypeTagType(dt){return{'UI显示':'','功能逻辑':'warning','数据内容':'danger','交互操作':'','性能稳定':'danger','跨端兼容':'warning'}[dt]||'info'}

// 显示状态对应的Bug列表
function showStatusBugList(status) {
  selectedStatus.value = status
  console.log('[showStatusBugList] rawBugs总数:', rawBugs.value.length)
  console.log('[showStatusBugList] 前3条rawBugs的status:', rawBugs.value.slice(0, 3).map(b => b.status || b['解决状态'] || b['bug状态'] || '空'))
  console.log('[showStatusBugList] statusData的keys:', Object.keys(statusData.value))
  // 从原始Bug数据中筛选对应状态的Bug
  statusBugList.value = rawBugs.value.filter(bug => {
    const bugStatus = bug.status || bug['解决状态'] || bug['bug状态'] || ''
    return bugStatus === status
  })
  statusBugDrawerVisible.value = true
  console.log(`[showStatusBugList] 状态"${status}"的Bug数量:`, statusBugList.value.length)
}
function formatAiSummary(t){
  if(!t)return''
  
  // 保留空行用于判断列表边界
  const lines = t.split('\n')
  let html = ''
  let inRiskList = false
  let inActionList = false
  let riskCounter = 0
  let actionCounter = 0
  let lastNum = 0
  
  // SVG 图标 - 设置固定尺寸
  const warningIcon = `<svg class="ai-icon" width="16" height="16" viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg"><path fill="#ef4444" d="M512 64a448 448 0 1 1 0 896 448 448 0 0 1 0-896zm0 192a58.432 58.432 0 0 0-58.24 63.744l23.36 256.384a35.072 35.072 0 0 0 69.76 0l23.36-256.384A58.432 58.432 0 0 0 512 256zm0 512a64 64 0 1 0 0-128 64 64 0 0 0 0 128z"/></svg>`
  const checkIcon = `<svg class="ai-icon" width="16" height="16" viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg"><path fill="#10b981" d="M512 64a448 448 0 1 1 0 896 448 448 0 0 1 0-896zm-6.656 545.024l-131.2-131.2a32 32 0 0 0-45.248 45.248l153.6 153.6a32 32 0 0 0 45.248 0l307.2-307.2a32 32 0 0 0-45.248-45.248l-284.352 284.8z"/></svg>`
  
  // 先找到第一个非空行作为概述
  let firstNonEmptyIdx = -1
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].trim() && !/^\d+[\.\、]/.test(lines[i].trim())) {
      firstNonEmptyIdx = i
      break
    }
  }
  
  if (firstNonEmptyIdx >= 0) {
    html += `<div class="ai-summary-overview">${lines[firstNonEmptyIdx].trim().replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')}</div>`
  }
  
  for (let i = firstNonEmptyIdx + 1; i < lines.length; i++) {
    const line = lines[i]
    const trimmed = line.trim()
    
    // 跳过空行，但用空行来判断列表边界
    if (!trimmed) {
      // 如果当前在风险列表中，且遇到了空行，后面又是1.开头，则关闭风险列表并准备开启行动建议
      if (inRiskList && i + 1 < lines.length) {
        let nextNonEmptyIdx = i + 1
        while (nextNonEmptyIdx < lines.length && !lines[nextNonEmptyIdx].trim()) {
          nextNonEmptyIdx++
        }
        if (nextNonEmptyIdx < lines.length && /^1[\.\、]/.test(lines[nextNonEmptyIdx].trim())) {
          inRiskList = false
          inActionList = true  // 标记接下来是行动建议列表
          html += '</div></div>'
        }
      }
      continue
    }
    
    // 检测列表项
    const listItemMatch = trimmed.match(/^(\d+)[\.\、]\s*(.+)$/)
    if (listItemMatch) {
      const num = parseInt(listItemMatch[1])
      const content = listItemMatch[2].replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      
      // 检测是否是第一个列表的开始（以1开头，且之前没有在列表中）
      if (num === 1 && !inRiskList && !inActionList) {
        inRiskList = true
        lastNum = 1
        riskCounter = 0
        html += `<div class="ai-summary-section"><div class="ai-summary-section-title">${warningIcon}关键风险点</div><div class="ai-summary-list risk-list">`
      }
      // 检测是否是第二个列表的开始（以1开头，但已经在风险列表中，且数字变小）
      else if (num === 1 && inRiskList && num < lastNum) {
        inRiskList = false
        html += '</div></div>'
        inActionList = true
        lastNum = 1
        actionCounter = 0
        html += `<div class="ai-summary-section"><div class="ai-summary-section-title">${checkIcon}行动建议</div><div class="ai-summary-list action-list">`
      }
      // 检测是否是通过空行预判后的行动建议列表开始
      else if (num === 1 && !inRiskList && inActionList && actionCounter === 0) {
        // 空行处理已设置 inActionList=true，这里创建行动建议标题
        lastNum = 1
        actionCounter = 0
        html += `<div class="ai-summary-section"><div class="ai-summary-section-title">${checkIcon}行动建议</div><div class="ai-summary-list action-list">`
      }
      
      // 添加列表项
      if (inRiskList) {
        riskCounter++
        html += `<div class="ai-summary-item risk-item"><span class="ai-summary-num risk-num">${riskCounter}</span><span class="ai-summary-text">${content}</span></div>`
      } else if (inActionList) {
        actionCounter++
        html += `<div class="ai-summary-item action-item"><span class="ai-summary-num action-num">${actionCounter}</span><span class="ai-summary-text">${content}</span></div>`
      }
      
      lastNum = num
    }
  }
  
  // 关闭未关闭的标签
  if (inRiskList || inActionList) {
    html += '</div></div>'
  }
  
  return html
}
function formatAiFocus(t){if(!t)return'';return t.split('\n').filter(l=>l.trim()).map(l=>`<div class="ai-focus-item">${l}</div>`).join('')}

// 解析测试关注点文本，返回对应的图标组件和清理后的文本
function parseFocusPoint(point) {
  if (!point) return { icon: null, text: '', type: 'default' }
  
  const iconMap = [
    { emoji: '🔴', icon: 'CircleClose', type: 'danger', label: '线上故障' },
    { emoji: '🔄', icon: 'Refresh', type: 'warning', label: '二次打开' },
    { emoji: '📌', icon: 'Flag', type: 'primary', label: '专项回归' },
    { emoji: '🚨', icon: 'AlarmClock', type: 'danger', label: '高危问题' },
    { emoji: '⚡', icon: 'Lightning', type: 'warning', label: '严重问题' },
    { emoji: '📝', icon: 'Document', type: 'info', label: '典型Bug' },
    { emoji: '⚠️', icon: 'Warning', type: 'warning', label: '警告' },
  ]
  
  for (const mapping of iconMap) {
    if (point.startsWith(mapping.emoji)) {
      return {
        icon: mapping.icon,
        text: point.slice(mapping.emoji.length).trim(),
        type: mapping.type,
        label: mapping.label
      }
    }
  }
  
  return { icon: null, text: point, type: 'default', label: '' }
}

// ==================== 核心方法 ====================
// ==================== 列表视图方法 ====================

// 触发文件选择
const triggerFileSelect = () => {
  fileInput.value.click()
}

// 处理文件选择（原生 input 方式）
const onFileSelected = (event) => {
  const file = event.target.files[0]
  if (!file) return

  // 验证文件格式
  if (!['.xlsx', '.xls'].includes(file.name.substring(file.name.lastIndexOf('.')).toLowerCase())) {
    ElMessage.error('请上传 .xlsx 或 .xls 格式的 Excel 文件')
    selectedFile.value = null
    fileName.value = ''
    return
  }

  selectedFile.value = file
  fileName.value = file.name
}

// 清除已选文件
const clearSelectedFile = () => {
  selectedFile.value = null
  fileName.value = ''
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

// 处理文件选择（el-upload 方式，保留兼容性）
const handleFileChange = async(file)=>{
  if(!file||!file.raw){
    fileName.value = ''
    selectedFile.value = null
    return
  }
  const rawFile=file.raw
  if(!['.xlsx','.xls'].includes(rawFile.name.substring(rawFile.name.lastIndexOf('.')).toLowerCase())){
    ElMessage.error('请上传 .xlsx 或 .xls 格式的 Excel 文件')
    fileName.value = ''
    selectedFile.value = null
    return
  }
  fileName.value=rawFile.name
  selectedFile.value=rawFile
}

// 开始分析
const startAnalysis = async()=>{
  if(!selectedFile.value){
    ElMessage.warning('请先选择文件')
    return
  }

  analyzing.value=true

  try{
    // 第一步：上传并获取基础分析结果（快速返回）
    const res=await analyzeBugExcel(selectedFile.value,{
      save:true,  // 默认保存到历史记录
      aiProvider:aiProvider.value,
      versionTag:versionTag.value || '',
      skip_ai: false
    })
    console.log('基础分析API响应:', res)
    const result=res.data||res

    if(result?.success){
      _rawAnalysisResult=result
      // 保存原始Bug数据
      rawBugs.value = result.raw_bugs || []
      console.log('[startAnalysis] raw_bugs数量:', rawBugs.value.length)
      try{
        applyAnalysisResult(result)
        console.log('applyAnalysisResult完成')
      }catch(e){console.error('applyAnalysisResult错误:', e)}
      try{
        generateSummary()
        console.log('generateSummary完成')
      }catch(e){console.error('generateSummary错误:', e)}

      // 立即显示基础分析结果
      analysisResult.value=true
      viewMode.value='detail'
      currentRecordId.value=result.record_id
      // 设置 currentRecord 以便页面标题正确显示文件名
      currentRecord.value = {
        id: result.record_id,
        file_name: result.file_name || selectedFile.value?.name || '未命名',
        version_tag: result.version_tag || versionTag.value || ''
      }
      // 更新URL，添加view和record_id参数
      router.replace({ query: { ...route.query, view: 'detail', record_id: result.record_id } })
      console.log('基础分析结果已显示')
      ElMessage.success(result.message||'基础分析完成')

      // 渲染图表
      nextTick(()=>{
        try{
          renderCharts()
          console.log('renderCharts完成')
        }catch(e){console.error('renderCharts错误:', e)}
      })

      // 加载历史记录（始终保存，自动刷新列表）
      if(result.record_id){
        try{await loadHistoryRecords()}catch(e){console.error('loadHistoryRecords错误:', e)}
      }

      // 第二步：如果后端标记需要AI增强，处理AI分析
      console.log('检查AI条件:', { ai_pending: result.ai_pending, record_id: result.record_id, aiProvider: aiProvider.value })
      aiLoading.value = true
      aiLoadingText.value = 'AI 正在分析中，请稍候...'
      
      if(result.ai_pending && aiProvider.value !== 'none'){
        if(result.record_id){
          console.log('开始AI增强分析(渐进式)...')
          setTimeout(() => {
            fetchAIEnhancement(result.record_id)
          }, 100)
        }else{
          console.log('无法启用AI分析: 无record_id')
          aiLoading.value = false
          if(result.ai_error){
            ElMessage.warning(result.ai_error)
          }else{
            ElMessage.warning('数据库模型不可用，请执行: python manage.py migrate')
          }
        }
      }else{
        console.log('AI未启用:', { ai_pending: result.ai_pending, aiProvider: aiProvider.value })
        aiLoading.value = false
      }
    }else{
      console.error('分析失败:', result)
      ElMessage.error(result?.error||'分析失败')
    }
  }catch(e){
    console.error('上传分析错误:', e)
    ElMessage.error(e.response?.data?.error||e.message||'分析失败，请检查文件格式')
  }
  finally{
    analyzing.value=false
    selectedFile.value=null
    // 清空文件输入框
    if (fileInput.value) {
      fileInput.value.value = ''
    }
  }
}

// 查看分析详情
const viewAnalysisDetail = async(record)=>{
  if(!record)return
  
  // 设置当前记录
  currentRecord.value = record
  currentRecordId.value = record.id
  fileName.value = record.file_name || '未命名'
  versionTag.value = record.version_tag || ''
  
  // 加载详情数据
  try{
    analyzing.value = true
    const res = await getBugAnalysisRecordDetail(record.id)
    console.log('[viewAnalysisDetail] 完整API响应:', res)
    console.log('[viewAnalysisDetail] res.data:', res.data)
    
    // 正确解析响应 - API返回的数据结构可能是：res 或 res.data
    let result
    if (res.data && res.data.analysis_result) {
      result = res.data
    } else if (res.analysis_result) {
      result = res
    } else {
      result = res.data || res
    }
    console.log('[viewAnalysisDetail] 解析后的result:', result)
    
    if(result?.analysis_result){
      _rawAnalysisResult = result.analysis_result
      console.log('[viewAnalysisDetail] analysis_result keys:', Object.keys(result.analysis_result))
      // 保存原始Bug数据
      rawBugs.value = result.raw_bugs || []
      console.log('[viewAnalysisDetail] raw_bugs数量:', rawBugs.value.length)
      try{
        applyAnalysisResult(result.analysis_result)
        console.log('applyAnalysisResult完成')
      }catch(e){console.error('applyAnalysisResult错误:', e)}
      try{
        generateSummary()
        console.log('generateSummary完成')
      }catch(e){console.error('generateSummary错误:', e)}
      
      // 恢复已缓存的AI模块分析结果 (从analysis_result中读取)
      const cachedAiModuleFocus = result.analysis_result?.aiModuleFocus
      console.log('[viewAnalysisDetail] 检查aiModuleFocus缓存:', {
        hasCached: !!cachedAiModuleFocus,
        keys: cachedAiModuleFocus ? Object.keys(cachedAiModuleFocus) : [],
        fullData: cachedAiModuleFocus
      })
      if(cachedAiModuleFocus && Object.keys(cachedAiModuleFocus).length > 0){
        // 创建一个新的对象来触发Vue的响应式更新 - 先清空再赋值
        aiModuleFocus.value = {}
        Object.assign(aiModuleFocus.value, cachedAiModuleFocus)
        console.log('[viewAnalysisDetail] ✅ 已恢复AI模块分析缓存:', Object.keys(cachedAiModuleFocus))
        console.log('[viewAnalysisDetail] 恢复后aiModuleFocus:', aiModuleFocus.value)
        console.log('[viewAnalysisDetail] aiModuleFocus的keys:', Object.keys(aiModuleFocus.value))
      } else {
        console.log('[viewAnalysisDetail] ⚠️ 没有可用的AI模块分析缓存')
      }
      
      // 切换到详情视图
      analysisResult.value = true
      viewMode.value = 'detail'
      currentRecordId.value = record.id
      
      // 更新URL，添加view和record_id参数
      router.replace({ query: { ...route.query, view: 'detail', record_id: record.id } })
      
      // 渲染图表
      nextTick(()=>{
        try{
          renderCharts()
          console.log('renderCharts完成')
        }catch(e){console.error('renderCharts错误:', e)}
      })
    }
    
    // 如果AI还在加载中，启动轮询
    if(result?.ai_pending && result.record_id){
      aiLoading.value = true
      aiLoadingText.value = 'AI 正在分析中，请稍候...'
      setTimeout(() => {
        fetchAIEnhancement(result.record_id)
      }, 100)
    }
  }catch(e){
    console.error('加载详情失败:', e)
    ElMessage.error('加载分析详情失败')
  }finally{
    analyzing.value = false
  }
}

// 删除记录
const handleDeleteRecord = async(record)=>{
  if(!record?.id)return
  
  try{
    await ElMessageBox.confirm(
      `确定要删除分析记录 "${record.file_name || '未命名'}" 吗？此操作不可恢复。`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await deleteBugAnalysisRecord(record.id)
    ElMessage.success('删除成功')
    
    // 刷新列表
    await loadHistoryRecords()
  }catch(error){
    if(error !== 'cancel'){
      console.error('删除失败:', error)
      ElMessage.error('删除失败，请重试')
    }
  }
}

// 返回列表
const backToList = ()=>{
  viewMode.value = 'list'
  // 重置当前记录
  currentRecord.value = null
  currentRecordId.value = null
  analysisResult.value = false
  resetAnalysisData()
  // 清除URL中的view参数
  const { view, ...otherQuery } = route.query
  router.replace({ query: otherQuery })
}

// 搜索
const handleSearch = ()=>{
  loadHistoryRecords()
}

// 格式化日期时间
const formatDateTime = (datetime)=>{
  if(!datetime)return '-'
  const date = new Date(datetime)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

// AI 增强分析（异步）- 注意：aiLoading已在调用前设置
const fetchAIEnhancement = async(recordId)=>{
  try{
    const res=await enhanceWithAI(recordId,{
      aiProvider:aiProvider.value,
      aiConfigId:null
    })
    console.log('AI增强API响应:', res)
    const result=res.data||res

    if(result?.success){
      // 应用AI增强结果
      if(result.aiSummary) aiSummary.value=result.aiSummary
      if(result.aiTestFocus) aiTestFocus.value=result.aiTestFocus
      if(result.aiRootCause) aiRootCause.value=result.aiRootCause
      if(result.aiRisks) aiRisks.value=result.aiRisks
      if(result.aiKeywords) aiKeywords.value=result.aiKeywords

      // 更新原始结果
      if(_rawAnalysisResult){
        _rawAnalysisResult.aiSummary=result.aiSummary
        _rawAnalysisResult.aiTestFocus=result.aiTestFocus
        _rawAnalysisResult.aiRootCause=result.aiRootCause
      }

      // AI关键词更新后，重新渲染关键词图表
      renderKeywordChart()

      // 自动为所有模块生成智能分析 (新功能)
      await fetchAllModulesIntelligentFocus(recordId)

      ElMessage.success(`AI 分析完成 (耗时${result.elapsed_ms||0}ms)`)
      console.log('AI增强结果已应用')
    }else{
      console.error('AI增强失败:', result)
      ElMessage.warning(result?.error||'AI 分析失败')
    }
  }catch(e){
    console.error('AI增强错误:', e)
    ElMessage.error(e.response?.data?.error||e.message||'AI 分析请求失败')
  }finally{
    aiLoading.value=false
  }
}

// 切换板块展开/收起状态
function toggleSection(sectionKey){
  sectionCollapsed.value[sectionKey] = !sectionCollapsed.value[sectionKey]
}

function applyAnalysisResult(result){
  modulesData.value=result.modulesData||{}; featureDetailData.value=result.featureDetailData||[]; severityCrossData.value=result.severityCrossData||{}
  sevInfData.value=result.sevInfData||{}; sevData.value=result.sevData||{}; statusData.value=result.statusData||{}; priorityData.value=result.priorityData||{}
  kwData.value=result.kwData||[]; timelineCleanData.value=result.timelineCleanData||{}; timelineData.value=result.timelineData||{}
  creatorModuleData.value=result.creatorModuleData||[]; participantData.value=result.participantData||[]; customFieldCharts.value=result.customFieldCharts||{}
  riskData.value=result.riskData||{P0:{total:0,detail:{}},P1:{total:0,detail:{}},P2:{total:0,detail:{}}}
  clusterData.value=result.clusterData||[]; rootCauseData.value=result.rootCauseData||[]; testFocusData.value=result.testFocusData||{}; metaData.value=result.metaData||{}
  aiSummary.value=result.aiSummary||''; aiTestFocus.value=result.aiTestFocus||{}; aiRootCause.value=result.aiRootCause||[]; aiRisks.value=result.aiRisks||{}; aiKeywords.value=result.aiKeywords||[]
  // 恢复AI模块分析缓存
  console.log('[applyAnalysisResult] 检查aiModuleFocus:', result.aiModuleFocus)
  if(result.aiModuleFocus && Object.keys(result.aiModuleFocus).length > 0){
    // 创建一个新的对象来触发Vue的响应式更新
    aiModuleFocus.value = {}
    Object.assign(aiModuleFocus.value, result.aiModuleFocus)
    console.log('[applyAnalysisResult] ✅ 已恢复aiModuleFocus:', Object.keys(result.aiModuleFocus))
    console.log('[applyAnalysisResult] 恢复后aiModuleFocus:', aiModuleFocus.value)
  } else {
    console.log('[applyAnalysisResult] ⚠️ 没有aiModuleFocus数据')
  }
  // 只在 record_id 存在时才更新，避免覆盖已设置的值
  if(result.record_id){
    currentRecordId.value=result.record_id
  }
}

async function loadHistoryRecords(){
  loadingHistory.value=true
  try{
    const params = { 
      page: currentPage.value,
      page_size: pageSize.value 
    }
    if(searchQuery.value){
      params.search = searchQuery.value
    }
    const r=await getBugAnalysisRecords(params)
    historyRecords.value=(r.data?.data?.items||r.data?.results||[])
    total.value = r.data?.data?.total || r.data?.total || 0
  }
  catch(e){console.warn('加载历史记录失败:',e)}
  finally{loadingHistory.value=false}
}

// 分页事件处理
const handleSizeChange = (val) => {
  pageSize.value = val
  loadHistoryRecords()
}

const handleCurrentChange = (val) => {
  currentPage.value = val
  loadHistoryRecords()
}

// AI 分析状态轮询
function startAiPolling(recordId) {
  if (aiPollingTimer) clearInterval(aiPollingTimer)
  aiPollingTimer = setInterval(async () => {
    try {
      const res = await getBugAnalysisAiStatus(recordId)
      const data = res.data?.data || res.data || {}
      aiStatus.value = data.ai_status || 'none'
      aiProgress.value = data.ai_progress || 0

      if (aiStatus.value === 'completed') {
        stopAiPolling()
        aiLoading.value = false
        // AI 分析完成，重新加载记录详情
        const detailRes = await getBugAnalysisRecordDetail(recordId)
        const detailData = detailRes.data?.data || detailRes.data || {}
        if (detailData.analysis_result) {
          _rawAnalysisResult = detailData.analysis_result
          // 恢复原始Bug数据（用于饼图点击筛选）
          rawBugs.value = detailData.raw_bugs || detailData.analysis_result?.raw_bugs || []
          console.log('[startAiPolling] AI完成，恢复rawBugs数量:', rawBugs.value.length)
          applyAnalysisResult(detailData.analysis_result)
          nextTick(() => {
            renderCharts()
            generateSummary()
          })
        }
        ElMessage.success('AI 智能分析完成')
      } else if (aiStatus.value === 'failed') {
        stopAiPolling()
        aiLoading.value = false
        ElMessage.error('AI 分析失败，请稍后手动重试')
      }
    } catch (e) {
      console.warn('查询AI状态失败:', e)
    }
  }, 3000)  // 每3秒轮询一次
}

function stopAiPolling() {
  if (aiPollingTimer) {
    clearInterval(aiPollingTimer)
    aiPollingTimer = null
  }
}

async function loadHistoryRecord(rec){
  loadingModuleDetail.value=true
  try{
    const r=await getBugAnalysisRecordDetail(rec.id)
    console.log('[加载历史记录] API原始响应:', r)
    console.log('[加载历史记录] r.data:', r.data)
    
    // 正确解析响应（支持多种格式）
    const rawData = r.data || r
    let result
    if (rawData && rawData.analysis_result) {
      result = rawData
    } else if (rawData && rawData.data && rawData.data.analysis_result) {
      result = rawData.data
    } else if (r.analysis_result) {
      result = r
    } else {
      result = rawData
    }
    console.log('[加载历史记录] result对象:', result)
    console.log('[加载历史记录] result.analysis_result:', result?.analysis_result)
    console.log('[加载历史记录] result.ai_status:', result?.ai_status)
    if(result.analysis_result){
      _rawAnalysisResult=result.analysis_result
      console.log('[加载历史记录] analysis_result:', result.analysis_result)
      console.log('[加载历史记录] analysis_result keys:', Object.keys(result.analysis_result))
      console.log('[加载历史记录] aiKeywords:', result.analysis_result?.aiKeywords)
      // 先设置 currentRecordId，再 applyAnalysisResult
      currentRecordId.value=rec.id
      // 恢复原始Bug数据（用于饼图点击筛选）
      rawBugs.value = result.raw_bugs || result.analysis_result?.raw_bugs || []
      console.log('[加载历史记录] rawBugs数量:', rawBugs.value.length)
      applyAnalysisResult(result.analysis_result)
      generateSummary()
      analysisResult.value=true
      
      // 恢复已缓存的AI模块分析结果 (从analysis_result中读取)
      const cachedAiModuleFocus = result.analysis_result?.aiModuleFocus
      console.log('[加载历史记录] 检查aiModuleFocus缓存:', {
        hasCached: !!cachedAiModuleFocus,
        keys: cachedAiModuleFocus ? Object.keys(cachedAiModuleFocus) : [],
        fullData: cachedAiModuleFocus
      })
      if(cachedAiModuleFocus && Object.keys(cachedAiModuleFocus).length > 0){
        // 创建一个新的对象来触发Vue的响应式更新
        aiModuleFocus.value = {}
        Object.assign(aiModuleFocus.value, cachedAiModuleFocus)
        console.log('[加载历史记录] ✅ 已恢复AI模块分析缓存:', Object.keys(cachedAiModuleFocus))
        console.log('[加载历史记录] 恢复后aiModuleFocus:', aiModuleFocus.value)
        console.log('[加载历史记录] aiModuleFocus的keys:', Object.keys(aiModuleFocus.value))
      } else {
        console.log('[加载历史记录] ⚠️ 没有可用的AI模块分析缓存')
      }
      
      // 先设置AI状态，再切换视图，确保详情页渲染时状态已就绪
      aiStatus.value = result.ai_status || 'none'
      aiProgress.value = result.ai_progress || 0
      console.log('[加载历史记录] 设置aiStatus:', aiStatus.value, 'aiProgress:', aiProgress.value)
      
      // 切换到详情视图并更新URL
      viewMode.value = 'detail'
      currentRecord.value = rec
      router.replace({ query: { ...route.query, view: 'detail', record_id: rec.id } })
      
      nextTick(()=>{
        renderCharts()
        console.log('[加载历史记录] 图表渲染完成，当前 aiKeywords:', aiKeywords.value)
      })
      ElMessage.success(`已加载: ${rec.file_name||rec.version_tag}`)

      // 如果 AI 分析在后台进行中，启动轮询并显示加载状态
      if (aiStatus.value === 'pending' || aiStatus.value === 'running') {
        aiLoading.value = true
        aiLoadingText.value = 'AI 正在分析中，请稍候...'
        startAiPolling(rec.id)
      }
    }
  }catch(e){ElMessage.error('加载历史记录失败')} finally{loadingModuleDetail.value=false}
}

async function openModuleDetail(modName){
  if(!currentRecordId.value){ElMessage.info('仅支持查看已保存记录的模块详情');return}
  selectedModule.value=modName; moduleDrawerVisible.value=true; loadingModuleDetail.value=true
  bugFilter.value={keyword:'',severity:'',defectType:''}; bugPage.value=1
  const localInfo=testFocusData.value[modName]; selectedModuleStats.value=localInfo||{}
  try{
    const r=await getModuleDetail(currentRecordId.value,modName,{page_size:100}); const data=r.data||r
    selectedModuleStats.value=data.stats||localInfo||{}; moduleBugs.value=data.bugs||[]
    if(data.ai_test_focus&&!aiTestFocus.value[modName])aiTestFocus.value[modName]=data.ai_test_focus
    if(data.ai_root_cause&&!aiRootCause.value.find(r=>r.module===modName))aiRootCause.value.push({module:modName,cause:data.ai_root_cause})
    // 异步获取智能模块分析 (不阻塞主流程)
    loadIntelligentModuleFocus(modName)
  }catch(e){console.warn('获取模块详情API失败:',e); moduleBugs.value=[]}finally{loadingModuleDetail.value=false}
}

// 加载智能模块分析 (三层架构) - 使用队列机制避免并行
async function loadIntelligentModuleFocus(modName){
  if(!currentRecordId.value||!modName)return
  // 检查缓存
  if(aiModuleFocus.value[modName])return
  
  // 如果已在队列或正在分析，直接返回
  if(analyzeQueue.value.includes(modName) || currentAnalyzingModule.value === modName){
    return
  }
  
  // 添加到队列等待处理
  analyzeQueue.value.push(modName)
  moduleFocusLoading.value[modName] = true
  processAnalyzeQueue()
}

// 为所有模块批量生成智能分析（使用队列机制）
async function fetchAllModulesIntelligentFocus(recordId){
  const modules = Object.keys(testFocusData.value)
  if(!modules.length || !recordId){
    console.log('[AI] 没有需要分析的模块')
    return
  }
  
  console.log(`[AI] 开始批量分析 ${modules.length} 个模块...`)
  
  // 过滤掉已有缓存的模块
  const modulesToAnalyze = modules.filter(m => !aiModuleFocus.value[m])
  
  if(!modulesToAnalyze.length){
    console.log('[AI] 所有模块已有缓存')
    return
  }
  
  // 将所有模块添加到队列
  for(const modName of modulesToAnalyze){
    if(!analyzeQueue.value.includes(modName) && currentAnalyzingModule.value !== modName){
      analyzeQueue.value.push(modName)
      moduleFocusLoading.value[modName] = true
    }
  }
  
  // 触发队列处理
  processAnalyzeQueue()
  
  console.log(`[AI] 已将 ${modulesToAnalyze.length} 个模块加入分析队列`)
}

// 分析单个模块（带全局锁和队列机制）
async function analyzeSingleModule(moduleName) {
  console.log('[AI] analyzeSingleModule被调用，模块名:', moduleName)
  console.log('[AI] 当前状态:', {
    currentRecordId: currentRecordId.value,
    analyzeQueue: analyzeQueue.value,
    currentAnalyzingModule: currentAnalyzingModule.value,
    aiModuleFocus: aiModuleFocus.value
  })
  
  if(!currentRecordId.value){
    ElMessage.warning('请先选择一个分析记录')
    return
  }
  
  // 如果该模块已在队列中，提示用户
  if(analyzeQueue.value.includes(moduleName) || moduleName === currentAnalyzingModule.value){
    ElMessage.info(`模块 "${moduleName}" 已在分析队列中`)
    return
  }
  
  // 如果该模块已分析完成，提示用户
  if(aiModuleFocus.value[moduleName]){
    ElMessage.success(`模块 "${moduleName}" 已完成AI分析`)
    return
  }
  
  // 添加到队列
  analyzeQueue.value.push(moduleName)
  moduleFocusLoading.value[moduleName] = true
  console.log('[AI] 模块已加入队列，当前队列:', analyzeQueue.value)
  
  // 触发队列处理
  processAnalyzeQueue()
}

// 处理分析队列（串行执行，防止并行覆盖）
async function processAnalyzeQueue() {
  // 如果正在处理中，等待当前分析完成
  if(isProcessingQueue.value || currentAnalyzingModule.value) {
    console.log('[AI] 队列正在处理中或已有模块在分析，跳过此次触发')
    return
  }
  
  isProcessingQueue.value = true
  console.log('[AI] 开始处理队列，当前队列长度:', analyzeQueue.value.length)
  
  while(analyzeQueue.value.length > 0) {
    // 取出队列中的第一个模块
    const moduleName = analyzeQueue.value.shift()
    currentAnalyzingModule.value = moduleName
    console.log(`[AI] 开始分析模块: ${moduleName}`)
    
    try {
      const res = await analyzeModuleFocusIntelligent(currentRecordId.value, moduleName)
      console.log('[AI] 收到API响应:', res)
      // 解析返回数据 - 注意API返回的是 {success: true, ...data} 格式
      let resultData
      if (res.data && res.data.success) {
        resultData = res.data
      } else if (res.success) {
        resultData = res
      } else {
        resultData = res.data || res
      }
      console.log('[AI] 解析后的数据:', resultData)
      
      // 检查是否有有效数据
      const hasFocusPoints = 
        resultData?.focus_points || 
        resultData?.data?.focus_points ||
        (resultData?.success && resultData?.module_name)
      
      if(hasFocusPoints){
        // 确保响应式更新 - 创建新对象
        const newAiModuleFocus = { ...aiModuleFocus.value }
        newAiModuleFocus[moduleName] = resultData
        aiModuleFocus.value = newAiModuleFocus
        console.log(`[AI] 模块 ${moduleName} 分析完成:`, resultData.risk_level || '未知')
        console.log('[AI] 保存到aiModuleFocus:', aiModuleFocus.value[moduleName])
        console.log('[AI] 当前aiModuleFocus:', aiModuleFocus.value)
      } else {
        console.warn(`[AI] 模块 ${moduleName} 返回数据异常:`, resultData)
        ElMessage.warning(`模块 "${moduleName}" 分析返回数据异常`)
      }
    } catch(e) {
      console.error(`[AI] 模块 ${moduleName} 分析失败:`, e)
      ElMessage.error(`模块 "${moduleName}" 分析失败: ${e.message || '未知错误'}`)
    } finally {
      moduleFocusLoading.value[moduleName] = false
      currentAnalyzingModule.value = ''
      console.log(`[AI] 模块 ${moduleName} 处理完成，当前队列长度:`, analyzeQueue.value.length)
    }
    
    // 小延迟，避免请求过快
    if(analyzeQueue.value.length > 0) {
      await new Promise(resolve => setTimeout(resolve, 500))
    }
  }
  
  isProcessingQueue.value = false
  
  // 队列处理完成后，如果有已完成的分析，给出提示
  if(Object.keys(aiModuleFocus.value).length > 0) {
    ElMessage.success('AI分析完成')
  }
}

// 用户手动触发AI分析所有模块（已弃用，保留兼容）
async function analyzeAllModules(){
  ElMessage.info('请使用各模块卡片上的"AI智能分析"按钮进行单独分析')
}

function handleCardClick(event, moduleName) {
  // 检查点击事件是否来自于AI按钮区域
  const target = event.target
  const isButtonClick = 
    target.closest('.ai-analyze-action') || 
    target.closest('.el-button') ||
    target.tagName === 'BUTTON'
  
  console.log('[CardClick] 点击事件:', {
    isButtonClick,
    target: target.tagName,
    moduleName
  })
  
  // 如果是AI按钮区域，不打开详情页面
  if (isButtonClick) {
    console.log('[CardClick] 点击了AI按钮区域，不打开详情')
    event.stopPropagation()
    return
  }
  
  // 否则正常打开详情页面
  console.log('[CardClick] 点击了卡片非按钮区域，打开详情')
  openModuleDetail(moduleName)
}

function onModuleChartClick(event){
  const names=Object.keys(modulesData.value)
  if(event.event&&event.target&&event.data!==undefined){
    const idx=event.dataIndex!==undefined?event.dataIndex:event.data
    if(idx>=0&&idx<names.length){
      const moduleName = names[idx]
      // 滚动到对应的模块卡片
      scrollToModuleCard(moduleName)
    }
  }
}

// 滚动到指定模块卡片
async function scrollToModuleCard(moduleName){
  // 先切换到测试重点Tab
  if(activeTab.value !== 'focus'){
    console.log('[联动] 切换到测试重点Tab:', moduleName)
    activeTab.value = 'focus'
    // 等待DOM更新
    await nextTick()
    // 给一点时间让卡片渲染完成
    await new Promise(resolve => setTimeout(resolve, 100))
  }
  
  const cardEl = moduleCardRefs.value[moduleName]
  if(!cardEl){
    console.warn('[联动] 未找到模块卡片:', moduleName)
    return
  }
  
  // 设置高亮
  highlightedModule.value = moduleName
  
  // 滚动到卡片位置
  cardEl.scrollIntoView({ behavior: 'smooth', block: 'center' })
  
  // 3秒后移除高亮
  setTimeout(() => {
    if(highlightedModule.value === moduleName){
      highlightedModule.value = ''
    }
  }, 3000)
  
  console.log('[联动] 已定位到模块:', moduleName)
}

async function doExport(){
  exporting.value=true
  try{
    let c='# Bug 回归测试清单\n\n> 生成时间:'+new Date().toLocaleString()+' | 来源:'+(metaData.value.input_file||'-')+'\n\n## 总览\n- 总Bug数:'+metaData.value.total_bugs+'- P0/P1/P2:'+(sevInfData.value['推断P0']||0)+'/'+(sevInfData.value['推断P1']||0)+'/'+(sevInfData.value['推断P2']||0)+'\n\n'
    let targetMods=[]
    if(exportScope.value==='all')targetMods=Object.keys(modulesData.value)
    else if(exportScope.value==='top5')targetMods=Object.entries(modulesData.value).sort((a,b)=>b[1]-a[1]).slice(0,5).map(([m])=>m)
    else targetMods=exportCustomMods.value
    for(const mod of targetMods){
      const info=testFocusData.value[mod]; if(!info)continue
      c+=`### ${mod} (${info.total}条)\n\n`
      c+=`- **总数**: ${info.total} | **线上**: ${info.online} | **二次打开**: ${info.reopened}\n`
      if(info.focus_points){for(const fp of info.focus_points)c+=`- ${fp}\n`}
      const af=getAiTestFocus(mod); if(af)c+=`\n**AI 建议:**\n${af}\n`
      c+='\n---\n\n'
    }
    const blob=new Blob([c],{type:'text/markdown;charset=utf-8'}); const url=URL.createObjectURL(blob); const a=document.createElement('a')
    a.href=url; a.download=`回归清单_${metaData.value.input_file?.replace('.xlsx','')||'bug'}_${Date.now()}.md`; a.click(); URL.revokeObjectURL(url)
    showExportDialog.value=false; ElMessage.success('导出成功!')
  }catch(e){ElMessage.error('导出失败: '+e.message)} finally{exporting.value=false}
}

// ==================== 摘要生成 ====================
const generateSummary=()=>{
  const lines=[],actions=[]
  const total=metaData.value?.total_bugs||0
  const sevGen=severityCrossData.value['3-一般']||{}, sP0=sevGen['P0']||0, sP1=sevGen['P1']||0
  if(sP0>0||sP1>0)lines.push(`<b>1) 严重度标注偏低：</b>"3-一般"中${sP0}条应为P0(白屏/504)、${sP1}条应为P1(无法/报错)，实际风险远高于标注。建议重新评审P0/P1候选Bug。`)
  const top3=Object.entries(modulesData.value).sort((a,b)=>b[1]-a[1]).slice(0,4).filter(([_,c])=>c>0)
  if(top3.length>0)lines.push(`<b>2) Bug聚集集中在${top3.map(([m,c])=>`${m}(${c})`).join('、')}：</b>这些模块是质量攻坚的重点方向。`)
  if((metaData.value?.uncategorized_pct||0)>20)lines.push(`<b>3) 标签规范待改善：</b>${metaData.value.uncategorized}条Bug归"其他"(${metaData.value.uncategorized_pct}%)，建议强制要求提Bug必须带【功能标签】+【端标签】。`)
  if(metaData.value?.import_count>0)lines.push(`<b style="color:#999;font-size:13px">数据说明：</b>本看板分析${total}条全量Bug。时间趋势图额外排除了${metaData.value.import_count}条平台迁移导入Bug。`)
  const p0T=riskData.value.P0?.total||0, p0D=riskData.value.P0?.detail||{}, p1O=riskData.value.P1?.detail?.['线上故障P1']||0, p1R=riskData.value.P1?.detail?.['二次回归']||0, p2O=riskData.value.P2?.detail?.['线上故障P2']||0
  if(p0T>0)actions.push(`<b>立即：</b>复核${p0T}条P0候选Bug(含白屏${p0D['白屏']||0}+504超时${p0D['504超时']||0}+闪退${p0D['闪退/崩溃']||0})，确认是否升级严重度。`)
  if((metaData.value?.uncategorized_pct||0)>20)actions.push('<b>本周：</b>强制推行Bug标签规范——提Bug必须带【功能标签】+【端标签】，消灭"其他"垃圾桶。')
  if(p1O>0||p2O>0)actions.push(`<b>持续：</b>重点模块安排专项回归测试——优先覆盖P1级线上故障${p1O}条+二次回归${p1R}条，P2级线上故障${p2O}条按需覆盖。`)
  summaryLines.value=lines; actionLines.value=actions
}

// ==================== 图表渲染 ====================
const renderCharts=()=>{renderModuleChart();renderSeverityCrossChart();renderSeverityPieChart();renderStatusChart();renderPriorityChart();renderKeywordChart();renderCreatorChart();renderParticipantChart();renderCustomFieldCharts();renderTimelineChart()}

const renderModuleChart=()=>{
  if(!moduleChartRef.value)return
  // 检查是否已有实例，有则先销毁
  let existingChart = echarts.getInstanceByDom(moduleChartRef.value)
  if(existingChart){existingChart.dispose()}
  const chart=echarts.init(moduleChartRef.value)
  const d=modulesData.value
  // 按Bug数量从高到低排序
  const sortedEntries=Object.entries(d).sort((a,b)=>b[1]-a[1])
  const names=sortedEntries.map(([k])=>k), values=sortedEntries.map(([,v])=>v)
  chart.setOption({
    backgroundColor:'#fff',title:{text:'Bug模块分布(核心模块)',textStyle:{color:'#7b42f6',fontSize:14}},tooltip:{trigger:'axis'},
    xAxis:{type:'category',data:names,axisLabel:{color:'#333',rotate:35,fontSize:11},axisLine:{lineStyle:{color:'#ccc'}}},
    yAxis:{type:'value',axisLabel:{color:'#333'},axisLine:{lineStyle:{color:'#ccc'}},splitLine:{lineStyle:{color:'#e0e0e0'}}},
    series:[{type:'bar',data:values,itemStyle:{color:new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:'#e53935'},{offset:1,color:'#ffcdd2'}])},label:{show:true,position:'top',color:'#333',fontSize:11}}],
    grid:{left:'10%',bottom:'22%',top:'15%'}
  })
  // 绑定点击事件 - 联动到测试重点卡片
  chart.off('click')
  chart.on('click', (params) => {
    if(params && params.name){
      scrollToModuleCard(params.name)
    }
  })
}
const renderSeverityCrossChart=()=>{
  if(!severityCrossChartRef.value)return
  let existingChart = echarts.getInstanceByDom(severityCrossChartRef.value)
  if(existingChart){existingChart.dispose()}
  const chart=echarts.init(severityCrossChartRef.value)
  const d=severityCrossData.value, labels=Object.keys(d).sort()
  // P0/P1/P2 对应中文严重度
  const typeMap={'P0':'致命','P1':'严重','P2':'一般'}
  const types=['P0','P1','P2'], typeLabels=['致命','严重','一般'], colors=['#e53935','#f59e0b','#22c55e']
  const series=types.map((t,i)=>({name:typeLabels[i],type:'bar',stack:'total',data:labels.map(s=>d[s][t]||0),itemStyle:{color:colors[i]},label:{show:false}}))
  chart.setOption({backgroundColor:'#fff',tooltip:{trigger:'axis',axisPointer:{type:'shadow'}},legend:{data:typeLabels,textStyle:{color:'#333'},top:10},xAxis:{type:'category',data:labels,axisLabel:{color:'#333',fontSize:12},axisLine:{lineStyle:{color:'#ccc'}}},yAxis:{type:'value',axisLabel:{color:'#333'},axisLine:{lineStyle:{color:'#ccc'}},splitLine:{lineStyle:{color:'#e0e0e0'}}},series,grid:{left:'15%',right:'5%',top:'20%',bottom:'10%'}})
}
const renderSeverityPieChart=()=>{
  if(!severityPieChartRef.value)return
  let existingChart = echarts.getInstanceByDom(severityPieChartRef.value)
  if(existingChart){existingChart.dispose()}
  const chart=echarts.init(severityPieChartRef.value)
  const data=Object.entries(sevInfData.value).map(([k,v])=>({name:k,value:v}))
  chart.setOption({backgroundColor:'#fff',tooltip:{trigger:'item',formatter:'{b}: {c}条 ({d}%)'},series:[{type:'pie',radius:['40%','60%'],center:['50%','50%'],avoidLabelOverlap:true,data,label:{show:true,position:'outside',color:'#333',fontSize:11,formatter:'{b}: {c}条 ({d}%)',minMargin:5,edgeDistance:10},labelLine:{show:true,length:15,length2:20,smooth:true},itemStyle:{borderColor:'#fff',borderWidth:2},color:['#e53935','#f59e0b','#95a5a6','#22c55e']}]})}
const renderStatusChart=()=>{
  if(!statusChartRef.value)return
  let existingChart = echarts.getInstanceByDom(statusChartRef.value)
  if(existingChart){existingChart.dispose()}
  const chart=echarts.init(statusChartRef.value)
  const data=Object.entries(statusData.value).sort((a,b)=>b[1]-a[1]).map(([k,v])=>({name:k,value:v}))
  chart.setOption({backgroundColor:'#fff',tooltip:{trigger:'item',formatter:'{b}: {c}条 ({d}%)'},series:[{type:'pie',radius:['40%','60%'],center:['50%','50%'],avoidLabelOverlap:true,data,label:{show:true,position:'outside',color:'#333',fontSize:11,formatter:'{b}: {c}条 ({d}%)',minMargin:5,edgeDistance:10},labelLine:{show:true,length:15,length2:20,smooth:true},itemStyle:{borderColor:'#fff',borderWidth:2},color:['#22c55e','#95a5a6','#f59e0b','#3b82f6','#e53935','#7b42f6','#ef4444','#06b6d4','#64748b']}]})
  // 绑定点击事件 - 点击"暂不修复"或"不予解决"显示具体Bug列表
  chart.off('click')
  chart.on('click', (params) => {
    if(params && params.name){
      const clickableStatuses = ['暂不修复', '不予解决', '不修复', '不予修复', '挂起']
      if(clickableStatuses.includes(params.name)){
        showStatusBugList(params.name)
      }
    }
  })
}
const renderPriorityChart=()=>{
  if(!priorityChartRef.value)return
  let existingChart = echarts.getInstanceByDom(priorityChartRef.value)
  if(existingChart){existingChart.dispose()}
  const chart=echarts.init(priorityChartRef.value)
  const colors=['#ef4444','#e53935','#f59e0b','#3b82f6','#7b42f6','#64748b']
  const data=Object.entries(priorityData.value).sort((a,b)=>b[1]-a[1]).filter(([_,v])=>v>0).map(([k,v],i)=>({name:k,value:v,itemStyle:{color:colors[i%6]}}))
  chart.setOption({backgroundColor:'#fff',tooltip:{trigger:'item',formatter:'{b}: {c}条 ({d}%)'},series:[{type:'pie',radius:['40%','60%'],center:['50%','50%'],avoidLabelOverlap:true,data,label:{show:true,position:'outside',color:'#333',fontSize:11,formatter:'{b}: {c}条 ({d}%)',minMargin:5,edgeDistance:10},labelLine:{show:true,length:15,length2:20,smooth:true},itemStyle:{borderColor:'#fff',borderWidth:2}}]})}
const renderKeywordChart=()=>{
  if(!keywordChartRef.value)return
  // 销毁已有实例
  let existingChart = echarts.getInstanceByDom(keywordChartRef.value)
  if(existingChart){existingChart.dispose()}
  const chart = echarts.init(keywordChartRef.value)
  // 优先使用 AI 生成的关键词，没有则显示空
  const data = aiKeywords.value && aiKeywords.value.length > 0 ? aiKeywords.value : []
  console.log('[关键词图表] 数据:', data, 'aiKeywords:', aiKeywords.value)
  const names=data.map(e=>e[0]), values=data.map(e=>e[1])
  const titleText = data.length > 0 ? '关键词词频 Top 20(AI 语义提取)' : '关键词词频 (等待 AI 分析...)'
  chart.setOption({backgroundColor:'#fff',title:{text:titleText,textStyle:{color:'#7b42f6',fontSize:14}},tooltip:{formatter:p=>`${p.name}: ${p.value}条相关Bug`},xAxis:{type:'value',axisLabel:{color:'#333'},axisLine:{lineStyle:{color:'#ccc'}},splitLine:{lineStyle:{color:'#e0e0e0'}}},yAxis:{type:'category',data:names,inverse:true,axisLabel:{color:'#333',fontSize:12},axisLine:{lineStyle:{color:'#ccc'}}},series:[{type:'bar',data:values,itemStyle:{color:new echarts.graphic.LinearGradient(0,0,1,0,[{offset:0,color:'#ffcdd2'},{offset:1,color:'#e53935'}])},label:{show:true,position:'right',color:'#333'}}],grid:{left:'15%',right:'10%'}})
}
const renderCreatorChart=()=>{
  if(!creatorChartRef.value)return
  let existingChart = echarts.getInstanceByDom(creatorChartRef.value)
  if(existingChart){existingChart.dispose()}
  const chart=echarts.init(creatorChartRef.value)
  const data=creatorModuleData.value, modules=Object.keys(modulesData.value)
  const colors=['#e53935','#3b82f6','#f59e0b','#7b42f6','#22c55e','#ec4899','#06b6d4','#ef4444','#64748b','#10b981','#f97316','#a855f7']
  const series=modules.map((mod,i)=>({name:mod,type:'bar',stack:'module',data:data.map(d=>(d.modules&&d.modules[mod])||0),itemStyle:{color:colors[i%colors.length],borderColor:'#fff',borderWidth:1}}))
  series.push({name:'其他(低频/无标签)',type:'bar',stack:'module',data:data.map(d=>(d.modules&&d.modules['其他'])||0),itemStyle:{color:'#d5d8dc',borderColor:'#fff',borderWidth:1}})
  chart.setOption({backgroundColor:'#fff',tooltip:{trigger:'axis',axisPointer:{type:'shadow'},formatter:params=>{const d=data[params[0].dataIndex];let l=`${d.creator}(总${d.total}条,线上${d.online}条/${d.online_pct}%)<br/>`;params.forEach(p=>{if(p.value>0)l+=`${p.seriesName}:${p.value}条<br/>`});return l}},legend:{data:[...modules,'其他(低频/无标签)'],textStyle:{color:'#333',fontSize:11},orient:'vertical',right:10,top:'middle',itemGap:8,itemWidth:12,itemHeight:12},xAxis:{type:'value',axisLabel:{color:'#333'},axisLine:{lineStyle:{color:'#ccc'}},splitLine:{lineStyle:{color:'#e0e0e0'}}},yAxis:{type:'category',data:data.map(d=>`${d.creator}(${d.total}条,线上${d.online_pct}%)`),inverse:true,axisLabel:{color:'#333',fontSize:11},axisLine:{lineStyle:{color:'#ccc'}}},series,grid:{left:'20%',right:'18%',top:40}})
}
const renderParticipantChart=()=>{
  if(!participantChartRef.value)return
  let existingChart = echarts.getInstanceByDom(participantChartRef.value)
  if(existingChart){existingChart.dispose()}
  const chart=echarts.init(participantChartRef.value)
  // participantData 现为列表结构 [{participant, total, online, online_pct, modules}]
  const data=participantData.value, modules=Object.keys(modulesData.value)
  const colors=['#3b82f6','#f59e0b','#7b42f6','#22c55e','#ec4899','#06b6d4','#ef4444','#64748b','#10b981','#f97316','#a855f7','#e53935']
  const series=modules.map((mod,i)=>({name:mod,type:'bar',stack:'module',data:data.map(d=>(d.modules&&d.modules[mod])||0),itemStyle:{color:colors[i%colors.length],borderColor:'#fff',borderWidth:1}}))
  series.push({name:'其他(低频/无标签)',type:'bar',stack:'module',data:data.map(d=>(d.modules&&d.modules['其他'])||0),itemStyle:{color:'#d5d8dc',borderColor:'#fff',borderWidth:1}})
  chart.setOption({backgroundColor:'#fff',tooltip:{trigger:'axis',axisPointer:{type:'shadow'},formatter:params=>{const d=data[params[0].dataIndex];let l=`${d.participant}(总${d.total}条,线上${d.online}条/${d.online_pct}%)<br/>`;params.forEach(p=>{if(p.value>0)l+=`${p.seriesName}:${p.value}条<br/>`});return l}},legend:{data:[...modules,'其他(低频/无标签)'],textStyle:{color:'#333',fontSize:11},orient:'vertical',right:10,top:'middle',itemGap:8,itemWidth:12,itemHeight:12},xAxis:{type:'value',axisLabel:{color:'#333'},axisLine:{lineStyle:{color:'#ccc'}},splitLine:{lineStyle:{color:'#e0e0e0'}}},yAxis:{type:'category',data:data.map(d=>`${d.participant}(${d.total}条,线上${d.online_pct}%)`),inverse:true,axisLabel:{color:'#333',fontSize:11},axisLine:{lineStyle:{color:'#ccc'}}},series,grid:{left:'20%',right:'18%',top:40}})
}

const renderCustomFieldCharts=()=>{
  const charts = customFieldChartRefs.value
  const dataMap = customFieldCharts.value
  // 先清理旧实例
  Object.values(customFieldChartInstances.value).forEach(c => { if (c) c.dispose() })
  customFieldChartInstances.value = {}

  Object.entries(dataMap).forEach(([fieldName, fieldData]) => {
    const el = charts[fieldName]
    if (!el) return
    const chart = echarts.init(el)
    const data = Object.entries(fieldData).sort((a, b) => b[1] - a[1]).slice(0, 20)
    const names = data.map(e => e[0]), values = data.map(e => e[1])
    chart.setOption({
      backgroundColor: '#fff',
      title: { text: `${fieldName}分布 Top 20`, textStyle: { color: '#7b42f6', fontSize: 14 } },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: p => `${p.name}: ${p.value}条` },
      xAxis: { type: 'category', data: names, axisLabel: { color: '#333', rotate: 30, fontSize: 11 }, axisLine: { lineStyle: { color: '#ccc' } } },
      yAxis: { type: 'value', axisLabel: { color: '#333' }, axisLine: { lineStyle: { color: '#ccc' } }, splitLine: { lineStyle: { color: '#e0e0e0' } } },
      series: [{
        type: 'bar',
        data: values,
        itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: '#9b59b6' }, { offset: 1, color: '#e0e0e0' }]) },
        label: { show: true, position: 'top', color: '#333', fontSize: 11 }
      }],
      grid: { left: '5%', right: '5%', bottom: '18%', top: 50 }
    })
    customFieldChartInstances.value[fieldName] = chart
  })
}

const renderTimelineChart=()=>{
  if(!timelineChartRef.value)return
  let existingChart = echarts.getInstanceByDom(timelineChartRef.value)
  if(existingChart){existingChart.dispose()}
  const chart=echarts.init(timelineChartRef.value)
  const d=timelineCleanData.value, hasImport=metaData.value?.import_count>0
  chart.setOption({backgroundColor:'#fff',tooltip:{trigger:'axis',formatter:p=>`${p[0].name}<br/>新增Bug:${p[0].value}条`},xAxis:{type:'category',data:Object.keys(d),axisLabel:{color:'#333',rotate:30},axisLine:{lineStyle:{color:'#ccc'}}},yAxis:{type:'value',axisLabel:{color:'#333'},axisLine:{lineStyle:{color:'#ccc'}},splitLine:{lineStyle:{color:'#e0e0e0'}}},series:[{type:'line',data:Object.values(d),smooth:true,itemStyle:{color:'#e53935'},lineStyle:{color:'#e53935',width:3},areaStyle:{color:new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:'rgba(229,57,53,0.25)'},{offset:1,color:'rgba(229,57,53,0.05)'}])},markPoint:{data:[{type:'max',name:'峰值',label:{color:'#333'}}],itemStyle:{color:'#e53935'}}}],grid:{left:'10%',bottom:'18%',top:30}})
}

// 重置分析数据（保留在详情视图）
const resetAnalysisData = () => {
  fileName.value = ''
  currentRecordId.value = null
  aiSummary.value = ''
  aiTestFocus.value = {}
  aiRootCause.value = []
  aiRisks.value = {}
  aiKeywords.value = []
  aiModuleFocus.value = {}  // 重置AI模块分析缓存
  moduleCardRefs.value = {}  // 重置模块卡片引用
  rawBugs.value = []  // 重置原始Bug数据
  _rawAnalysisResult = null
  ;[moduleChartRef.value, severityCrossChartRef.value, severityPieChartRef.value, statusChartRef.value, priorityChartRef.value, keywordChartRef.value, creatorChartRef.value, participantChartRef.value, timelineChartRef.value].forEach(ref => { if (ref) { const c = echarts.getInstanceByDom(ref); if (c) c.dispose() } })
  // 清理自定义字段图表
  Object.values(customFieldChartInstances.value).forEach(c => { if (c) c.dispose() })
  customFieldChartInstances.value = {}
  customFieldChartRefs.value = {}
}

// 重置分析（返回列表并清空所有数据）
const resetAnalysis = () => {
  viewMode.value = 'list'
  analysisResult.value = false
  currentRecord.value = null
  currentRecordId.value = null
  resetAnalysisData()
  // 重置版本标签
  versionTag.value = ''
  showUploadDialog.value = true
}

// 监听 URL 参数变化，自动切换视图
watch(() => route.query.view, (newView) => {
  if (newView === 'detail') {
    viewMode.value = 'detail'
  } else {
    viewMode.value = 'list'
    // 如果是从详情页返回列表页，清理详情页数据
    if (!newView && currentRecordId.value) {
      currentRecord.value = null
      currentRecordId.value = null
      analysisResult.value = false
      resetAnalysisData()
    }
  }
}, { immediate: true })

// 监听 Tab 切换，当切换到图表 Tab 时重新渲染图表
watch(() => activeTab.value, async (newTab) => {
  if (newTab === 'charts' && analysisResult.value) {
    // 等待 DOM 更新完成
    await nextTick()
    // 延迟一下确保容器已经可见
    setTimeout(() => {
      try {
        renderCharts()
        console.log('[Tab切换] 图表重新渲染完成')
      } catch (e) {
        console.error('[Tab切换] 图表渲染错误:', e)
      }
    }, 100)
  }
})

// 详情页刷新时恢复数据
const restoreDetailView = async () => {
  console.log('[restoreDetailView] 开始恢复, 状态:', {
    viewMode: viewMode.value,
    analysisResult: analysisResult.value,
    historyRecordsLength: historyRecords.value.length,
    recordIdFromUrl: route.query.record_id,
    query: route.query
  })
  
  // 如果当前是详情视图但没有数据，尝试恢复
  if (viewMode.value === 'detail' && !analysisResult.value) {
    const recordIdFromUrl = route.query.record_id
    
    if (recordIdFromUrl) {
      // 先尝试从历史记录列表中找
      let record = historyRecords.value.find(r => r.id === parseInt(recordIdFromUrl))
      
      if (record) {
        console.log('[恢复详情页] 从历史列表加载记录:', recordIdFromUrl)
        await loadHistoryRecord(record)
        return
      } else {
        // 如果历史记录列表中没有，直接通过ID加载
        console.log('[恢复详情页] 通过API加载记录:', recordIdFromUrl)
        try {
          const r = await getBugAnalysisRecordDetail(parseInt(recordIdFromUrl))
          const result = r.data || r
          if (result && result.analysis_result) {
            // 构造一个模拟的记录对象
            record = {
              id: parseInt(recordIdFromUrl),
              file_name: result.file_name || result.version_tag || `记录#${recordIdFromUrl}`,
              version_tag: result.version_tag || '',
              ...result
            }
            await loadHistoryRecord(record)
            return
          }
        } catch (e) {
          console.error('[恢复详情页] API加载记录失败:', e)
        }
      }
    }
    
    // 如果没有URL参数或加载失败，但有历史记录，加载第一条
    if (historyRecords.value.length > 0) {
      console.log('[恢复详情页] 加载第一条历史记录')
      await loadHistoryRecord(historyRecords.value[0])
    } else {
      console.log('[restoreDetailView] 无法恢复详情页:', {
        isDetail: viewMode.value === 'detail',
        noAnalysis: !analysisResult.value,
        hasRecordId: !!recordIdFromUrl,
        hasHistory: historyRecords.value.length > 0
      })
    }
  } else {
    console.log('[restoreDetailView] 条件不满足, 跳过恢复:', {
      isDetail: viewMode.value === 'detail',
      noAnalysis: !analysisResult.value
    })
  }
}

// 所有图表resize
const resizeAllCharts = () => {
  const chartRefs = [
    moduleChartRef.value,
    severityCrossChartRef.value,
    severityPieChartRef.value,
    statusChartRef.value,
    priorityChartRef.value,
    keywordChartRef.value,
    creatorChartRef.value,
    timelineChartRef.value
  ]
  chartRefs.forEach(ref => {
    if (ref) {
      const chart = echarts.getInstanceByDom(ref)
      if (chart) {
        chart.resize()
      }
    }
  })
}

// resize防抖
let resizeTimer = null
const handleResize = () => {
  if (resizeTimer) {
    clearTimeout(resizeTimer)
  }
  resizeTimer = setTimeout(() => {
    resizeAllCharts()
  }, 200)
}

onMounted(() => {
  loadHistoryRecords().then(() => {
    // 历史记录加载完成后，如果是详情视图则恢复数据
    restoreDetailView()
  })
  // 监听窗口resize
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  // 移除resize监听
  window.removeEventListener('resize', handleResize)
  if (resizeTimer) {
    clearTimeout(resizeTimer)
  }
  // 停止AI轮询
  stopAiPolling()
  // 销毁所有图表实例
  const chartRefs = [
    moduleChartRef.value,
    severityCrossChartRef.value,
    severityPieChartRef.value,
    statusChartRef.value,
    priorityChartRef.value,
    keywordChartRef.value,
    creatorChartRef.value,
    timelineChartRef.value
  ]
  chartRefs.forEach(ref => {
    if (ref) {
      const chart = echarts.getInstanceByDom(ref)
      if (chart) {
        chart.dispose()
      }
    }
  })
})

// ==================== 云效同步方法 ====================

// 搜索云效项目
async function searchYunxiaoProjects(keyword) {
  if (!yunxiaoForm.value.token) return
  yunxiaoProjectLoading.value = true
  try {
    const res = await getYunxiaoProjects({
      token: yunxiaoForm.value.token,
      organization_id: yunxiaoForm.value.organization_id,
      keyword: keyword || '',
      page: 1,
      per_page: 50,
    })
    if (res.data && res.data.success) {
      yunxiaoProjects.value = res.data.items || []
    } else {
      ElMessage.error((res.data && res.data.message) || '获取项目列表失败')
    }
  } catch (e) {
    ElMessage.error('获取项目列表失败: ' + (e.message || e))
  } finally {
    yunxiaoProjectLoading.value = false
  }
}

// 项目切换后加载迭代
async function onYunxiaoProjectChange() {
  yunxiaoForm.value.sprint_id = ''
  yunxiaoSprints.value = []
  if (!yunxiaoForm.value.space_id || !yunxiaoForm.value.token) return
  yunxiaoSprintLoading.value = true
  try {
    const res = await getYunxiaoSprints({
      token: yunxiaoForm.value.token,
      organization_id: yunxiaoForm.value.organization_id,
      space_id: yunxiaoForm.value.space_id,
      page: 1,
      per_page: 100,
    })
    if (res.data && res.data.success) {
      yunxiaoSprints.value = res.data.items || []
    } else {
      ElMessage.error((res.data && res.data.message) || '获取迭代列表失败')
    }
  } catch (e) {
    ElMessage.error('获取迭代列表失败: ' + (e.message || e))
  } finally {
    yunxiaoSprintLoading.value = false
  }
}

// 开始云效同步
async function startYunxiaoSync() {
  if (!yunxiaoForm.value.token || !yunxiaoForm.value.space_id) {
    ElMessage.warning('请填写访问令牌并选择项目')
    return
  }

  // 表单校验
  try {
    await yunxiaoFormRef.value.validate()
  } catch {
    return
  }

  analyzing.value = true
  ElMessage.info('正在从云效拉取 Bug 数据，请稍候...')

  try {
    // 获取迭代名称
    const sprintName = yunxiaoForm.value.sprint_id
      ? (yunxiaoSprints.value.find(s => s.id === yunxiaoForm.value.sprint_id)?.name || yunxiaoForm.value.sprint_id)
      : ''

    const res = await syncFromYunxiao({
      token: yunxiaoForm.value.token,
      organization_id: yunxiaoForm.value.organization_id,
      space_id: yunxiaoForm.value.space_id,
      sprint_id: yunxiaoForm.value.sprint_id || undefined,
      sprint_name: sprintName || undefined,
      version_tag: yunxiaoForm.value.version_tag,
      max_bugs: yunxiaoForm.value.max_bugs,
      ai_provider: aiProvider.value,
      skip_ai: false,
    })

    if (!res.data || !res.data.success) {
      ElMessage.error((res.data && res.data.message) || '同步失败')
      return
    }

    ElMessage.success((res.data && res.data.message) || '同步成功')
    showYunxiaoDialog.value = false

    // 清空表单
    yunxiaoForm.value = {
      token: yunxiaoForm.value.token,
      organization_id: yunxiaoForm.value.organization_id,
      space_id: '',
      sprint_id: '',
      version_tag: '',
      max_bugs: 1000,
    }
    yunxiaoProjects.value = []
    yunxiaoSprints.value = []

    // 跳转到详情视图展示结果
    analysisResult.value = true
    viewMode.value = 'detail'
    fileName.value = res.data.file_name || ''
    currentRecordId.value = res.data.record_id || null
    aiStatus.value = res.data.ai_status || 'none'
    aiProgress.value = 0

    // 将后端返回的数据解析到各个 ref（关键！否则图表和AI数据都为空）
    _rawAnalysisResult = res.data
    rawBugs.value = res.data.raw_bugs || []
    console.log('[startYunxiaoSync] raw_bugs数量:', rawBugs.value.length)
    applyAnalysisResult(res.data)

    // 清空选中文件状态
    selectedFile.value = null

    // 渲染图表
    nextTick(() => {
      renderCharts()
      generateSummary()
    })

    // 刷新历史记录
    loadHistoryRecords()

    // 如果 AI 分析在后台进行中，启动轮询
    if (aiStatus.value === 'pending' || aiStatus.value === 'running') {
      aiLoading.value = true
      aiLoadingText.value = 'AI 正在分析中，请稍候...'
      startAiPolling(currentRecordId.value)
    }
  } catch (e) {
    ElMessage.error('同步失败: ' + (e.message || e))
  } finally {
    analyzing.value = false
  }
}

// 打开同步日志对话框
async function openSyncLog(row) {
  if (!row?.id) return

  showSyncLogDialog.value = true
  syncLogLoading.value = true
  syncLogData.value = null

  try {
    const res = await getYunxiaoSyncLog(row.id)
    if (res.data && res.data.success) {
      syncLogData.value = res.data
    } else {
      ElMessage.error((res.data && res.data.message) || '获取同步日志失败')
      showSyncLogDialog.value = false
    }
  } catch (e) {
    ElMessage.error('获取同步日志失败: ' + (e.message || e))
    showSyncLogDialog.value = false
  } finally {
    syncLogLoading.value = false
  }
}

// 复制第一条Bug的JSON数据
function copyFirstBugFields() {
  if (!syncLogData.value?.first_bug_fields) return

  const jsonStr = JSON.stringify(syncLogData.value.first_bug_fields, null, 2)
  navigator.clipboard.writeText(jsonStr).then(() => {
    ElMessage.success('已复制到剪贴板')
  }).catch(() => {
    ElMessage.error('复制失败，请手动复制')
  })
}
</script>

<style scoped>
/* ==================== 设计系统变量 - 紫色主题 ==================== */
.bug-analysis-container {
  padding: 24px;
  min-height: calc(100vh - 60px);
  background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%);
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* ==================== 筛选栏 - 参考XMindConverter风格 ==================== */
.filter-bar {
  padding: 20px 24px;
  background: #ffffff;
  border: 1px solid rgba(147, 112, 219, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
  display: flex;
  align-items: center;
  gap: 12px;
}

.filter-bar :deep(.el-input__wrapper) {
  box-shadow: 0 0 0 1px rgba(147, 112, 219, 0.25);
  border-radius: 8px;
  background: #ffffff;
}

.filter-bar :deep(.el-input__wrapper:hover),
.filter-bar :deep(.el-input__wrapper:focus) {
  box-shadow: 0 0 0 1px #7b42f6;
}

.filter-bar-spacer {
  flex: 1;
}

/* 选择文件按钮 */
.select-file-btn {
  background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
  border: none;
  font-weight: 600;
  padding: 10px 20px;
}

.select-file-btn .el-icon {
  margin-right: 4px;
}

.select-file-btn:hover {
  background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(123, 66, 246, 0.4);
}

.select-file-btn:disabled {
  background: #d1d5db;
  transform: none;
  box-shadow: none;
}

/* 已选文件信息展示 */
.selected-file-info {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 6px 6px 14px;
  background: #f8f7ff;
  border: 1px solid rgba(123, 66, 246, 0.12);
  border-radius: 8px;
  transition: all 0.25s ease;
}

.selected-file-info:hover {
  background: #f0edff;
  border-color: rgba(123, 66, 246, 0.2);
}

.selected-file-info .file-name-text {
  font-size: 14px;
  font-weight: 600;
  color: #5a32a3;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.selected-file-info .file-name-text.clickable {
  cursor: pointer;
  padding: 4px 8px;
  margin: -4px -8px;
  border-radius: 6px;
  transition: all 0.2s ease;
}

.selected-file-info .file-name-text.clickable:hover {
  background: rgba(123, 66, 246, 0.08);
}

/* ==================== 卡片容器 - 统一风格 ==================== */
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

/* ==================== 页面标题 ==================== */
.page-header{text-align:center;margin-bottom:28px;padding:12px 0}
.page-title{font-size:26px;font-weight:600;color:#5a32a3;display:flex;align-items:center;justify-content:center;gap:10px;margin:0;letter-spacing:-0.02em}
.page-title .el-icon{color:#7b42f6;font-size:28px}
.page-subtitle{color:#7b6db3;font-size:14px;margin-top:10px;font-weight:400}

/* ==================== 上传区域 - 紫色主题 ==================== */
.upload-card{max-width:720px;margin:48px auto;border-radius:12px;background:#fff;border:1px solid rgba(147,112,219,0.12);box-shadow:0 4px 16px rgba(147,112,219,0.08);transition:all 0.3s ease}
.upload-card:hover{box-shadow:0 8px 24px rgba(147,112,219,0.12);border-color:rgba(147,112,219,0.2)}
.upload-area{width:100%;padding:48px 0;background:linear-gradient(135deg, #f8f7ff 0%, #f5f3ff 100%);border:2px dashed rgba(147,112,219,0.3);border-radius:8px;transition:all 0.3s ease}
.upload-area:hover{border-color:#7b42f6;background:linear-gradient(135deg, #f0edff 0%, #e8e4ff 100%)}
.upload-icon{font-size:52px;color:#a888e0;margin-bottom:16px;transition:all 0.3s ease}
.upload-area:hover .upload-icon{color:#7b42f6;transform:scale(1.05)}
.upload-icon.is-loading{animation:spin 1.2s linear infinite;color:#7b42f6}
@keyframes spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}

.upload-text{text-align:center}.upload-text p{margin:10px 0}
.upload-text em{color:#7b42f6;font-style:normal;font-weight:600;cursor:pointer;position:relative}
.upload-text em::after{content:'';position:absolute;bottom:-2px;left:0;width:100%;height:2px;background:#7b42f6;transform:scaleX(0);transition:transform 0.3s ease}
.upload-text em:hover::after{transform:scaleX(1)}

.analyzing-text{color:#7b42f6;display:flex;align-items:center;justify-content:center;gap:8px;font-weight:500}
.upload-tip{font-size:12px;color:#94a3b8;margin-top:4px}

.ai-options{margin-top:24px;padding:0 24px}
.ai-options :deep(.el-divider__text){background:#fff;color:#64748b;font-size:13px;padding:0 16px}
.template-tips{margin-top:20px;padding:0 24px 16px}
.template-tips :deep(.el-alert){border-radius:8px;border:none}

/* ==================== 操作栏 - 紫色主题 ==================== */
.analysis-result{position:relative}.result-actions{display:flex;gap:12px;margin-bottom:24px;flex-wrap:wrap;align-items:center}
.result-actions .el-button{border-radius:8px;font-weight:500;padding:10px 20px;transition:all 0.3s ease}
.result-actions .el-button--primary{
  background:linear-gradient(135deg,#7b42f6 0%,#5a32a3 100%);
  border-color:#7b42f6;
  box-shadow:0 4px 12px rgba(123,66,246,0.3)
}
.result-actions .el-button--primary:hover{
  background:linear-gradient(135deg,#6d33e6 0%,#4a249c 100%);
  border-color:#6d33e6;
  transform:translateY(-1px);
  box-shadow:0 6px 16px rgba(123,66,246,0.4)
}
.history-badge{margin-left:6px}

/* ==================== 历史侧边栏 - 紫色主题 ==================== */
.history-sidebar {
  position: absolute;
  right: 0;
  top: 50px;
  width: 300px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.12);
  border: 1px solid rgba(147, 112, 219, 0.12);
  z-index: 10;
  max-height: calc(100vh - 100px);
  overflow-y: auto;
}
.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 18px;
  border-bottom: 1px solid rgba(147, 112, 219, 0.1);
  background: linear-gradient(90deg, #f8f7ff 0%, #fff 100%);
}
.history-title {
  font-weight: 600;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 8px;
  color: #5a32a3;
}
.history-list {
  padding: 10px;
}
.history-item {
  padding: 12px 14px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid transparent;
  margin-bottom: 6px;
}
.history-item:hover {
  background: #f8f7ff;
  transform: translateX(2px);
  border-color: rgba(147, 112, 219, 0.15);
}
.history-item.active {
  border-color: #7b42f6;
  background: #f0edff;
  box-shadow: 0 0 0 3px rgba(123, 66, 246, 0.1);
}
.history-item-main {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}
.history-item-name {
  font-weight: 500;
  font-size: 13px;
  color: #5a32a3;
}
.history-item-meta {
  display: flex;
  gap: 12px;
  margin-top: 6px;
  font-size: 11px;
  color: #7b6db3;
}
.top-mod {
  color: #ef4444;
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 500;
}

.main-content{transition:margin-right 0.3s ease}.main-content.with-sidebar{margin-right:320px}

/* ==================== 统计卡片 - 紫色主题 ==================== */
.summary-cards{margin-bottom:24px}
.summary-card{
  background:#fff;
  border-radius:12px;
  padding:20px 24px;
  display:flex;
  gap:16px;
  align-items:center;
  border:1px solid rgba(147,112,219,0.12);
  box-shadow:0 4px 16px rgba(147,112,219,0.08);
  transition:all 0.3s ease
}
.summary-card:hover{
  box-shadow:0 8px 24px rgba(147,112,219,0.12);
  transform:translateY(-2px);
  border-color:rgba(147,112,219,0.2)
}
.summary-icon{
  width:52px;
  height:52px;
  border-radius:14px;
  display:flex;
  align-items:center;
  justify-content:center;
  font-size:24px;
  flex-shrink:0;
  transition:all 0.3s ease;
  background:linear-gradient(135deg,#f5f3ff 0%,#ede9fe 100%);
  color:#7b42f6
}
.summary-card:hover .summary-icon{
  transform:scale(1.05);
  background:linear-gradient(135deg,#ede9fe 0%,#ddd6fe 100%)
}
.summary-info{flex:1}
.summary-value{font-size:28px;font-weight:700;color:#5a32a3;line-height:1.2}
.summary-label{font-size:14px;color:#7b6db3;margin-top:4px;font-weight:500}
.summary-sub{font-size:12px;color:#a898d8;margin-top:4px}

.card-tooltip-icon {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #f0f0f0;
  color: #999;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.3s;
}

.card-tooltip-icon:hover {
  background: #7b42f6;
  color: #fff;
}

.summary-card {
  position: relative;
}

/* ==================== 卡片组件 - 紫色主题 ==================== */
.section-card {
  margin-bottom: 24px;
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
  border: 1px solid rgba(147, 112, 219, 0.12);
  background: #fff;
  transition: all 0.3s ease;
}
.section-card:hover {
  box-shadow: 0 8px 24px rgba(147, 112, 219, 0.12);
  border-color: rgba(147, 112, 219, 0.2);
}
.section-card :deep(.el-card__header) {
  padding: 16px 20px;
  border-bottom: 1px solid rgba(147, 112, 219, 0.1);
  background: linear-gradient(90deg, #f8f7ff 0%, #fff 100%);
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.header-title {
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
  color: #5a32a3;
  font-size: 15px;
}
.header-title .el-icon {
  color: #7b42f6;
  font-size: 18px;
}

/* 头部操作区域 - AI分析按钮 */
.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}
.header-actions .el-tag {
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  white-space: nowrap !important;
  flex-shrink: 0 !important;
  gap: 4px !important;
  line-height: 1 !important;
}
.header-actions .el-tag .el-icon {
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
}
.header-actions .el-tag span {
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
}

.ai-analyze-btn {
  background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
  border-color: #7b42f6;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 4px;
}

.ai-analyze-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%);
  border-color: #6d33e6;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(123, 66, 246, 0.4);
}

.ai-analyze-btn:disabled {
  background: #c0c0c0;
  border-color: #c0c0c0;
  cursor: not-allowed;
}

/* ==================== 图表卡片 - 紫色主题 ==================== */
.chart-card {
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
  border: 1px solid rgba(147, 112, 219, 0.12);
  background: #fff;
  transition: all 0.3s ease;
}
.chart-card:hover {
  box-shadow: 0 8px 24px rgba(147, 112, 219, 0.12);
  border-color: rgba(147, 112, 219, 0.2);
}
.chart-card :deep(.el-card__header) {
  padding: 16px 20px;
  border-bottom: 1px solid rgba(147, 112, 219, 0.1);
  background: linear-gradient(90deg, #f8f7ff 0%, #fff 100%);
}
.chart-title {
  font-weight: 600;
  color: #5a32a3;
  display: flex;
  align-items: center;
  gap: 8px;
}

.chart-header-flex {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* ==================== AI 智能摘要样式 - 现代简约风格 ==================== */
:deep(.ai-summary-content) {
  padding: 8px 4px;
}

:deep(.ai-summary-overview) {
  font-size: 15px;
  line-height: 1.9;
  color: #4b5563;
  padding: 20px 24px;
  background: linear-gradient(135deg, #fef9e7 0%, #fdf3d2 100%);
  border-radius: 12px;
  border-left: 4px solid #f59e0b;
  margin-bottom: 28px;
  box-shadow: 0 2px 8px rgba(245, 158, 11, 0.08);
}

:deep(.ai-summary-overview strong) {
  color: #b45309;
  font-weight: 600;
}

:deep(.ai-summary-section) {
  margin-bottom: 28px;
}

:deep(.ai-summary-section-title) {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 15px;
  font-weight: 600;
  color: #374151;
  margin-bottom: 16px;
  padding: 0 4px 12px 4px;
  border-bottom: 1px solid #e5e7eb;
  letter-spacing: 0.3px;
}

:deep(.ai-summary-section-title .ai-icon) {
  font-size: 18px;
  width: 18px;
  height: 18px;
}

:deep(.ai-summary-list) {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 0 4px;
}

:deep(.ai-summary-item) {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 18px 22px;
  background: #ffffff;
  border-radius: 10px;
  border: 1px solid #f3f4f6;
  transition: all 0.25s ease;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

:deep(.ai-summary-item:hover) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

:deep(.ai-summary-item.risk-item) {
  background: linear-gradient(135deg, #fff5f7 0%, #ffeef2 100%);
  border: 1px solid rgba(239, 68, 68, 0.2);
}

:deep(.ai-summary-item.risk-item:hover) {
  background: linear-gradient(135deg, #ffeef2 0%, #ffe8ed 100%);
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.15);
}

:deep(.ai-summary-item.action-item) {
  background: linear-gradient(135deg, #f0fdf4 0%, #ecfdf5 100%);
  border-color: #bbf7d0;
}

:deep(.ai-summary-item.action-item:hover) {
  background: linear-gradient(135deg, #dcfce7 0%, #d1fae5 100%);
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.1);
}

:deep(.ai-summary-num) {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 28px;
  height: 28px;
  border-radius: 50%;
  font-size: 13px;
  font-weight: 600;
  flex-shrink: 0;
  position: relative;
}

:deep(.ai-summary-num.risk-num) {
  background: linear-gradient(135deg, #fff5f7 0%, #ffeef2 100%);
  border: 1px solid rgba(239, 68, 68, 0.2);
  color: #e53935;
  box-shadow: 0 2px 6px rgba(229, 57, 53, 0.2);
}

:deep(.ai-summary-num.action-num) {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: white;
  box-shadow: 0 2px 6px rgba(16, 185, 129, 0.3);
}

:deep(.ai-summary-text) {
  flex: 1;
  font-size: 14.5px;
  line-height: 1.75;
  color: #4b5563;
  padding-top: 2px;
}

:deep(.ai-summary-text strong) {
  color: #1f2937;
  font-weight: 600;
}

/* ==================== AI 状态标签样式 ==================== */
.ai-status-tag {
  border-radius: 12px;
  padding: 4px 12px;
  font-weight: 500;
  font-size: 12px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.ai-status-tag.success {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
  color: white !important;
  border: none !important;
  box-shadow: 0 2px 8px rgba(16, 185, 129, 0.3);
}

.ai-status-tag.loading {
  background: linear-gradient(135deg, #f8f7ff 0%, #f0edff 100%) !important;
  color: #7b42f6 !important;
  border: 1px solid rgba(147, 112, 219, 0.3) !important;
}

.ai-status-tag .el-icon {
  font-size: 12px;
}

/* ==================== AI 进度条 - 现代渐变风格 ==================== */
.ai-progress-banner {
  margin-bottom: 16px;
  background: linear-gradient(135deg, #e8f5e9 0%, #f3e5f5 100%);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.ai-banner-content {
  display: flex;
  align-items: center;
  padding: 16px 20px;
  gap: 16px;
}

.ai-banner-icon {
  width: 40px;
  height: 40px;
  background: linear-gradient(135deg, #9c27b0 0%, #673ab7 100%);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.ai-pulse-icon {
  font-size: 20px;
  color: #fff;
  animation: ai-pulse 1.5s ease-in-out infinite;
}

@keyframes ai-pulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.1); opacity: 0.8; }
}

.ai-banner-text {
  flex: 1;
}

.ai-banner-title {
  font-size: 15px;
  font-weight: 600;
  color: #333;
  margin-bottom: 4px;
}

.ai-banner-desc {
  font-size: 13px;
  color: #666;
  line-height: 1.5;
}

.ai-banner-progress {
  display: flex;
  align-items: center;
}

.ai-progress-ring {
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, #fff 0%, #f5f5f5 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 3px solid #e0e0e0;
  position: relative;
  overflow: hidden;
}

.ai-progress-ring::before {
  content: '';
  position: absolute;
  inset: -3px;
  border-radius: 50%;
  background: conic-gradient(#9c27b0 var(--progress, 35%), #e0e0e0 var(--progress, 35%));
  animation: rotate-ring 2s linear infinite;
}

.ai-progress-value {
  font-size: 13px;
  font-weight: 700;
  color: #9c27b0;
  z-index: 1;
}

@keyframes rotate-ring {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.ai-progress-bar {
  height: 3px;
  background: #e0e0e0;
  overflow: hidden;
}

.ai-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #9c27b0 0%, #673ab7 50%, #9c27b0 100%);
  background-size: 200% 100%;
  animation: progress-flow 1.5s ease-in-out infinite;
  transition: width 0.3s ease;
}

@keyframes progress-flow {
  0% { background-position: 0% 0%; }
  50% { background-position: 100% 0%; }
  100% { background-position: 0% 0%; }
}

/* ==================== AI 风险加载状态 ==================== */
.ai-risk-loading {
  padding: 24px;
  background: linear-gradient(135deg, #fff5f7 0%, #fafafa 100%);
  border-radius: 12px;
  border: 1px solid rgba(239, 68, 68, 0.15);
}

.ai-risk-loading .ai-loading-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
}

.ai-risk-loading .ai-loading-pulse {
  width: 40px;
  height: 40px;
  background: linear-gradient(135deg, #fff5f7 0%, #ffeef2 100%);
  border: 1px solid rgba(239, 68, 68, 0.2);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.ai-risk-loading .ai-loading-pulse .el-icon {
  color: #e53935;
  font-size: 20px;
}

.ai-risk-loading .ai-loading-info {
  flex: 1;
}

.ai-risk-loading .ai-loading-title {
  font-size: 15px;
  font-weight: 600;
  color: #333;
  margin-bottom: 4px;
}

.ai-risk-loading .ai-loading-desc {
  font-size: 13px;
  color: #666;
}

.ai-risk-card {
  background: linear-gradient(135deg, #fafafa 0%, #f5f5f5 100%);
  border: 1px solid rgba(147, 112, 219, 0.15);
}

.ai-risk-card .card-header .header-title {
  color: #7b42f6;
}

.ai-risk-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.ai-risk-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 16px;
  background: #fff;
  border-radius: 8px;
  border: 1px solid #e8e8e8;
}

.ai-risk-item .el-tag {
  flex-shrink: 0;
}

.ai-risk-desc {
  flex: 1;
  font-size: 14px;
  color: #333;
  line-height: 1.5;
}

/* ==================== AI 风险分析结果 - 现代卡片风格 ==================== */
.ai-risk-result {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.ai-risk-level-block {
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.p0-block {
  background: linear-gradient(135deg, #fff5f5 0%, #ffebee 100%);
  border: 2px solid #ffcdd2;
}

.p1-block {
  background: linear-gradient(135deg, #fff8e1 0%, #ffecb3 100%);
  border: 2px solid #ffe0b2;
}

.p2-block {
  background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
  border: 2px solid #a5d6a7;
}

.risk-level-header {
  display: flex;
  align-items: center;
  padding: 16px 20px;
  gap: 16px;
}

/* P0区块 - 淡红风格，类似平台浅紫 */
.p0-block .risk-level-header {
  background: linear-gradient(135deg, #fff5f7 0%, #ffeef2 100%);
  border: 1px solid rgba(239, 68, 68, 0.2);
}

.p0-block .risk-level-icon {
  background: rgba(239, 68, 68, 0.1);
}

.p0-block .risk-level-icon .el-icon {
  color: #e53935;
}

.p0-block .level-name {
  color: #e53935;
}

.p0-block .level-desc {
  color: rgba(192, 57, 43, 0.85);
}

.p0-block .risk-level-count {
  background: rgba(239, 68, 68, 0.08);
}

.p0-block .count-num {
  color: #e53935;
}

.p0-block .count-label {
  color: rgba(192, 57, 43, 0.85);
}

/* P1区块 - 淡黄风格，类似平台浅紫 */
.p1-block .risk-level-header {
  background: linear-gradient(135deg, #fffaf0 0%, #fff5e6 100%);
  border: 1px solid rgba(245, 158, 11, 0.2);
}

.p1-block .risk-level-icon {
  background: rgba(245, 158, 11, 0.1);
}

.p1-block .risk-level-icon .el-icon {
  color: #f59e0b;
}

.p1-block .level-name {
  color: #f59e0b;
}

.p1-block .level-desc {
  color: rgba(204, 126, 34, 0.85);
}

.p1-block .risk-level-count {
  background: rgba(245, 158, 11, 0.08);
}

.p1-block .count-num {
  color: #f59e0b;
}

.p1-block .count-label {
  color: rgba(204, 126, 34, 0.85);
}

/* P2区块 - 淡绿风格，类似平台浅紫 */
.p2-block .risk-level-header {
  background: linear-gradient(135deg, #f0fdf4 0%, #ecfdf5 100%);
  border: 1px solid rgba(34, 197, 94, 0.2);
}

.p2-block .risk-level-icon {
  background: rgba(34, 197, 94, 0.1);
}

.p2-block .risk-level-icon .el-icon {
  color: #22c55e;
}

.p2-block .level-name {
  color: #22c55e;
}

.p2-block .level-desc {
  color: rgba(39, 174, 96, 0.85);
}

.p2-block .risk-level-count {
  background: rgba(34, 197, 94, 0.08);
}

.p2-block .count-num {
  color: #22c55e;
}

.p2-block .count-label {
  color: rgba(39, 174, 96, 0.85);
}

.risk-level-icon {
  width: 44px;
  height: 44px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.risk-level-icon .el-icon {
  font-size: 24px;
  color: #fff;
}

.risk-level-title {
  flex: 1;
}

.level-name {
  font-size: 18px;
  font-weight: 700;
  color: #fff;
  display: block;
}

.level-desc {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.85);
  margin-top: 2px;
}

.risk-level-count {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.15);
  border-radius: 8px;
}

.count-num {
  font-size: 24px;
  font-weight: 700;
  color: #fff;
}

.count-label {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
}

.risk-items-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px 20px 20px;
}

.risk-item-card {
  background: rgba(255, 255, 255, 0.6);
  border-radius: 8px;
  padding: 12px 16px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  transition: all 0.2s;
}

.risk-item-card:hover {
  background: rgba(255, 255, 255, 0.9);
  border-color: rgba(0, 0, 0, 0.12);
  transform: none;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.p0-item {
  border-left: 3px solid #e53935;
}

.p1-item {
  border-left: 3px solid #f59e0b;
}

.p2-item {
  border-left: 3px solid #22c55e;
}

.p0-item:hover {
  border-left-color: #c0392b;
  background: rgba(255, 255, 255, 0.95);
}

.p1-item:hover {
  border-left-color: #d97706;
  background: rgba(255, 255, 255, 0.95);
}

.p2-item:hover {
  border-left-color: #16a34a;
  background: rgba(255, 255, 255, 0.95);
}

.risk-item-content {
  font-size: 14px;
  color: #333;
  line-height: 1.7;
}

.risk-item-content .risk-type {
  font-weight: 600;
  color: #555;
  margin-right: 4px;
}

.risk-item-content .risk-desc {
  color: #666;
  line-height: 1.7;
}

/* P0风险类型 - 加深红色 */
.p0-item .risk-type {
  color: #c0392b;
  font-weight: 700;
}

/* P1风险类型 - 加深黄色 */
.p1-item .risk-type {
  color: #d68910;
  font-weight: 700;
}

/* P2风险类型 - 加深绿色 */
.p2-item .risk-type {
  color: #1e8449;
  font-weight: 700;
}

.ai-generated-mark {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 20px;
  background: linear-gradient(135deg, #f3e5f5 0%, #e1bee7 100%);
  border-radius: 8px;
  color: #9c27b0;
  font-size: 13px;
}

.ai-generated-mark .el-icon {
  font-size: 16px;
}

/* ==================== AI 加载状态 - 现代骨架屏风格 ==================== */
.ai-loading-container {
  padding: 24px;
  background: linear-gradient(135deg, #fafafa 0%, #f5f5f5 100%);
  border-radius: 12px;
  border: 1px solid rgba(147, 112, 219, 0.15);
}

.ai-loading-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
}

.ai-loading-pulse {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: linear-gradient(135deg, #f3e5f5 0%, #e1bee7 100%);
  border: 1px solid rgba(147, 112, 219, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
}

.ai-loading-pulse .el-icon {
  color: #7b42f6;
  font-size: 20px;
}

.ai-loading-info {
  flex: 1;
}

.ai-loading-title {
  font-size: 15px;
  font-weight: 600;
  color: #333;
  margin-bottom: 4px;
}

.ai-loading-desc {
  font-size: 13px;
  color: #666;
}

.ai-skeleton {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.ai-skeleton-line {
  height: 12px;
  background: linear-gradient(90deg, #e2e8f0 25%, #f1f5f9 50%, #e2e8f0 75%);
  background-size: 200% 100%;
  border-radius: 6px;
  animation: shimmer 1.5s ease-in-out infinite;
}

.ai-skeleton-line:nth-child(1) { width: 100%; }
.ai-skeleton-line:nth-child(2) { width: 85%; }
.ai-skeleton-line:nth-child(3) { width: 70%; }

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

@keyframes pulse-highlight {
  0%, 100% { box-shadow: 0 0 0 3px rgba(245,158,11,0.3), 0 8px 16px -4px rgba(245,158,11,0.2); }
  50% { box-shadow: 0 0 0 6px rgba(245,158,11,0.15), 0 12px 24px -4px rgba(245,158,11,0.3); }
}

.summary-content{padding:4px 0}.summary-section{margin-bottom:16px}.summary-section:last-child{margin-bottom:0}
.summary-title{font-weight:600;font-size:14px;margin-bottom:8px;display:flex;align-items:center;gap:6px}
.summary-title.danger{color:#ef4444}.summary-title.warning{color:#f59e0b}
.summary-list{padding-left:4px}.summary-item{font-size:13px;line-height:1.8;color:#64748b;padding:2px 0}

.chart-row{margin-bottom:24px}
.chart-container{height:350px;width:100%}.clickable-chart{cursor:pointer}.chart-note{margin-top:8px}

.risk-section{margin-bottom:20px}.risk-section:last-child{margin-bottom:0}.risk-title{font-size:15px;margin-bottom:10px;padding-left:4px}
.risk-title.p0{color:#ef4444;border-left:3px solid #ef4444}.risk-title.p1{color:#f59e0b;border-left:3px solid #f59e0b}.risk-title.p2{color:#3b82f6;border-left:3px solid #3b82f6}

/* ==================== 测试重点卡片网格布局 - 等高设计 ==================== */
.focus-section-header {
  margin-bottom: 20px;
  padding: 16px 20px;
  background: #fff;
  border-radius: 12px;
  border: 1px solid rgba(147, 112, 219, 0.12);
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
}

.focus-section-header .card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.focus-cards-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  align-items: stretch;
}

.focus-card-wrapper {
  display: flex;
  height: 100%;
}

.focus-card {
  border: 1px solid rgba(147, 112, 219, 0.1);
  border-radius: 16px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  background: #fff;
  display: flex;
  flex-direction: column;
  box-shadow: 0 2px 8px rgba(147, 112, 219, 0.06), 0 1px 3px rgba(0, 0, 0, 0.04);
  flex: 1;
  min-height: 320px;
  max-height: 420px;
  overflow: hidden;
}

.focus-card:hover {
  border-color: rgba(123, 66, 246, 0.25);
  box-shadow: 0 12px 40px -10px rgba(123, 66, 246, 0.18), 0 4px 16px rgba(0, 0, 0, 0.06);
  transform: translateY(-3px);
}

.focus-card.clickable {
  cursor: pointer;
}

.focus-card.highlighted {
  border-color: #f59e0b;
  box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.12), 0 12px 32px -8px rgba(245, 158, 11, 0.2);
  transform: translateY(-2px);
  animation: pulse-highlight 1.5s ease-in-out;
}

@keyframes pulse-highlight {
  0%, 100% { box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.12), 0 12px 32px -8px rgba(245, 158, 11, 0.2); }
  50% { box-shadow: 0 0 0 5px rgba(245, 158, 11, 0.18), 0 12px 32px -8px rgba(245, 158, 11, 0.25); }
}

/* ==================== 卡片头部 - 更突出的设计 ==================== */
.focus-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 14px;
  border-bottom: 1px solid rgba(147, 112, 219, 0.08);
  min-width: 0;
  gap: 12px;
  flex-shrink: 0;
}

.focus-header .el-tag {
  display: inline-flex;
  align-items: center;
  flex-shrink: 0;
}

.focus-name {
  font-weight: 700;
  font-size: 17px;
  color: #1e1b4b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  min-width: 0;
  letter-spacing: -0.3px;
}

.focus-badges {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  justify-content: flex-end;
  align-items: center;
}

/* ==================== 卡片内容区域 - 固定高度可滚动 ==================== */
.focus-body {
  font-size: 13px;
  color: #475569;
  display: flex;
  flex-direction: column;
  gap: 12px;
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding-right: 4px;
}

.focus-body::-webkit-scrollbar {
  width: 4px;
}

.focus-body::-webkit-scrollbar-track {
  background: transparent;
}

.focus-body::-webkit-scrollbar-thumb {
  background: rgba(147, 112, 219, 0.2);
  border-radius: 2px;
}

.focus-body::-webkit-scrollbar-thumb:hover {
  background: rgba(147, 112, 219, 0.35);
}

.focus-stats {
  display: flex;
  gap: 16px;
  margin-bottom: 4px;
  font-size: 12px;
  color: #64748b;
  font-weight: 500;
  flex-shrink: 0;
}

.focus-stats span {
  display: flex;
  align-items: center;
  gap: 4px;
}

.focus-points {
  padding-left: 0;
  margin: 0;
  list-style: none;
}

.focus-points li {
  line-height: 1.5;
  padding: 6px 0;
  border-bottom: 1px solid rgba(226, 232, 240, 0.5);
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 13px;
}

.focus-points li:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.focus-points li:first-child {
  padding-top: 0;
}

.base-focus-points {
  margin-top: 0;
}
/* ==================== 带图标的测试关注点样式 - 优化版 ==================== */
.focus-point-item-with-icon {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px 0;
  border-bottom: 1px solid rgba(226, 232, 240, 0.4);
}

.focus-point-item-with-icon:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.focus-point-icon {
  margin-top: 1px;
  font-size: 14px;
  flex-shrink: 0;
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.focus-point-text {
  flex: 1;
  line-height: 1.5;
  color: #475569;
  font-size: 13px;
}
/* 图标颜色样式 */
.focus-icon-danger { color: #ef4444 }
.focus-icon-warning { color: #f59e0b }
.focus-icon-success { color: #22c55e }
.focus-icon-info { color: #3b82f6 }
.focus-icon-primary { color: #7b42f6 }

/* ==================== AI智能分析区域标题 ==================== */
.ai-section-title {
  font-size: 12px;
  font-weight: 700;
  color: #7b42f6;
  margin: 0 0 10px;
  padding: 6px 10px;
  background: linear-gradient(135deg, #f8f7ff 0%, #f5f3ff 100%);
  border-radius: 8px;
  border-left: 3px solid #7b42f6;
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.base-section-title {
  font-size: 12px;
  font-weight: 600;
  color: #475569;
  margin: 12px 0 8px;
  padding: 6px 10px;
  background: #f8fafc;
  border-radius: 8px;
  border-left: 3px solid #94a3b8;
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}
.ai-focus-preview{margin-top:12px;padding:12px 16px;background:#f0fdf4;border-radius:10px;border:1px solid #bbf7d0}
.ai-focus-label{font-size:13px;color:#16a34a;font-weight:600;display:flex;align-items:center;gap:6px}
.ai-focus-text{font-size:13px;color:#15803d;margin-top:6px;line-height:1.7}

.detail-section{margin-bottom:24px}.detail-section-title{font-size:15px;font-weight:700;color:#1e1b4b;margin-bottom:12px;display:flex;align-items:center;gap:8px}
.module-stats-desc{margin-bottom:20px}
.dtype-tags{display:flex;flex-wrap:wrap;gap:6px}
.ai-section{background:linear-gradient(135deg,#f8f7ff 0%,#f5f3ff 100%);border-radius:12px;padding:16px;border:1px solid rgba(147,112,219,0.12)}
.ai-title{color:#7b42f6!important}.ai-content{font-size:14px;line-height:1.8;color:#475569}.cause-content{font-style:italic;color:#64748b}
.focus-points-list{padding-left:0;list-style:none}.focus-points-list li{line-height:1.7;font-size:14px;padding:8px 0;border-bottom:1px solid rgba(226,232,240,0.5)}.focus-points-list li:last-child{border-bottom:none}
.focus-points-list .focus-point-item-with-icon{padding-left:0;margin-bottom:10px}
.bug-filter-bar{display:flex;gap:10px;margin-bottom:16px;flex-wrap:wrap}
.bug-list-section{margin-top:12px}

/* 智能模块分析样式 */
.intelligent-focus{background:linear-gradient(135deg,#f8fafc 0%,#f8f7ff 100%);border:1px solid rgba(147,112,219,0.15);border-radius:12px}
.intelligent-focus-content{min-height:80px}
.focus-points-intelligent{display:flex;flex-direction:column;gap:16px}
.focus-point-item{padding:16px;background:#fff;border-radius:12px;border-left:4px solid #cbd5e1;transition:all 0.2s ease;box-shadow:0 1px 3px rgba(0,0,0,0.05)}
.focus-point-item:hover{transform:translateX(4px);box-shadow:0 4px 12px rgba(0,0,0,0.08)}
.focus-point-item.high{border-left-color:#ef4444;background:#fef2f2}
.focus-point-item.medium{border-left-color:#f59e0b;background:#fffbeb}
.focus-point-item.low{border-left-color:#3b82f6;background:#eff6ff}
.point-header{display:flex;align-items:center;gap:10px;margin-bottom:8px}
.point-source{font-size:12px;color:#64748b;background:#f1f5f9;padding:4px 10px;border-radius:20px;font-weight:500}
.point-source.ai{color:#7c3aed;background:#ede9fe;font-weight:600}
.point-desc{font-size:14px;color:#334155;line-height:1.7;margin-bottom:8px}
.point-suggestion{font-size:13px;color:#059669;display:flex;align-items:flex-start;gap:6px;line-height:1.6;font-weight:500}
.point-root-cause{margin-top:6px}
.focus-loading-hint{text-align:center;color:#64748b;font-size:14px;padding:24px;font-weight:500}
.technical-insights{margin-top:16px}

/* ==================== AI分析卡片样式 - 优化版 ==================== */
.ai-focus-card {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.ai-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding-right: 4px;
}

.ai-body::-webkit-scrollbar {
  width: 4px;
}

.ai-body::-webkit-scrollbar-track {
  background: transparent;
}

.ai-body::-webkit-scrollbar-thumb {
  background: rgba(147, 112, 219, 0.2);
  border-radius: 2px;
}

.ai-body::-webkit-scrollbar-thumb:hover {
  background: rgba(147, 112, 219, 0.35);
}

/* AI智能分析点 - 紧凑卡片设计 */
.ai-point-item {
  padding: 10px 12px;
  background: #f8fafc;
  border-radius: 10px;
  border-left: 3px solid #cbd5e1;
  transition: all 0.2s ease;
  margin-bottom: 6px;
}

.ai-point-item:last-child {
  margin-bottom: 0;
}

.ai-point-item:hover {
  transform: translateX(2px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.ai-point-item.high {
  border-left-color: #ef4444;
  background: linear-gradient(135deg, #fef2f2 0%, #fff5f5 100%);
}

.ai-point-item.medium {
  border-left-color: #f59e0b;
  background: linear-gradient(135deg, #fffbeb 0%, #fffdf5 100%);
}

.ai-point-item.low {
  border-left-color: #3b82f6;
  background: linear-gradient(135deg, #eff6ff 0%, #f5f9ff 100%);
}

.ai-point-type {
  margin-bottom: 4px;
}

.ai-point-desc {
  font-size: 12px;
  color: #475569;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.more-points-hint {
  text-align: center;
  font-size: 11px;
  color: #94a3b8;
  padding: 6px;
  background: #f8fafc;
  border-radius: 6px;
  margin-top: 4px;
}
/* ==================== AI加载中卡片样式 ==================== */
.ai-loading-card {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.ai-loading-body {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: 40px 20px;
  background: linear-gradient(135deg, #f8fafc 0%, #f8f7ff 100%);
  border-radius: 12px;
  margin-top: 12px;
  flex: 1;
  border: 1px dashed rgba(147, 112, 219, 0.2);
}

.ai-loading-text {
  font-size: 13px;
  color: #64748b;
  margin-top: 12px;
  font-weight: 500;
}
/* 分析中标签样式 - 防止换行 */
.analyzing-tag{display:inline-flex!important;align-items:center!important;justify-content:center!important;white-space:nowrap!important;flex-shrink:0!important;gap:4px!important;line-height:1!important}
.analyzing-tag .el-icon{display:inline-flex!important;align-items:center!important;justify-content:center!important}
.analyzing-tag span{display:inline-flex!important;align-items:center!important;justify-content:center!important}
.queue-tag{display:inline-flex!important;align-items:center!important;justify-content:center!important;white-space:nowrap!important;flex-shrink:0!important;line-height:1!important}
/* ==================== 模块卡片中的AI分析按钮 - 优化版 ==================== */
.ai-analyze-action {
  margin-top: auto;
  padding-top: 12px;
  border-top: 1px solid rgba(226, 232, 240, 0.6);
  display: flex;
  justify-content: center;
  pointer-events: auto;
  position: relative;
  z-index: 100;
  cursor: default;
  flex-shrink: 0;
}

.ai-analyze-action .el-button {
  width: 100%;
  pointer-events: auto;
  z-index: 101;
  border-radius: 10px;
  height: 36px;
  font-weight: 600;
  font-size: 13px;
  letter-spacing: 0.3px;
  transition: all 0.2s ease;
  background: linear-gradient(135deg, #7b42f6 0%, #6d33e6 100%);
  border: none;
  box-shadow: 0 3px 10px rgba(123, 66, 246, 0.25);
}

.ai-analyze-action .el-button:hover {
  transform: translateY(-1px);
  box-shadow: 0 5px 14px rgba(123, 66, 246, 0.35);
}

.ai-analyze-action .el-button:active {
  transform: translateY(0);
}

.ai-analyze-action .el-button.is-disabled {
  opacity: 0.6;
  background: #cbd5e1;
  box-shadow: none;
}

.slide-fade-enter-active,.slide-fade-leave-active{transition:all 0.3s ease}
.slide-fade-enter-from{transform:translateX(30px);opacity:0}.slide-fade-leave-to{transform:translateX(30px);opacity:0}

/* Tab 标签页导航样式 */
.tab-navigation{display:flex;gap:12px;margin-bottom:24px;background:#fff;padding:8px;border-radius:12px;box-shadow:0 2px 12px rgba(0,0,0,0.06);border:1px solid rgba(147,112,219,0.1)}
.tab-item{flex:1;display:flex;align-items:center;justify-content:center;gap:8px;padding:14px 20px;border-radius:10px;cursor:pointer;transition:all 0.3s cubic-bezier(0.4,0,0.2,1);font-weight:500;color:#64748b;position:relative;overflow:hidden}
.tab-item:hover{background:rgba(123,66,246,0.04);color:#7b42f6}
.tab-item.active{background:linear-gradient(135deg,#7b42f6 0%,#6d33e6 100%);color:#fff;box-shadow:0 4px 14px rgba(123,66,246,0.35)}
.tab-item .el-icon{font-size:18px}
.tab-item span{font-size:14px}
.tab-badge{margin-left:4px}
.tab-content{min-height:400px}
.tab-panel{animation:fadeIn 0.4s ease}
.tab-panel-content{padding:4px}

/* 可折叠卡片样式 */
.collapsible-card{transition:all 0.3s ease}
.collapsible-header{cursor:pointer;user-select:none;display:flex;justify-content:space-between;align-items:center;transition:background-color 0.2s ease;padding:8px 12px;margin:-12px -20px;border-radius:8px}
.collapsible-header:hover{background-color:rgba(123,66,246,0.04)}
.header-right{display:flex;align-items:center;gap:12px}
.collapse-icon{font-size:16px;color:#94a3b8;transition:transform 0.3s cubic-bezier(0.4,0,0.2,1)}
.collapse-icon.is-collapsed{transform:rotate(-90deg)}
.collapsible-content{animation:fadeIn 0.3s ease}
@keyframes fadeIn{from{opacity:0;transform:translateY(-10px)}to{opacity:1;transform:translateY(0)}}

.export-options{padding:8px 0}

/* ==================== 导出按钮 - 紫色主题 ==================== */
.export-confirm-btn {
  background: linear-gradient(135deg, #7b42f6 0%, #6d33e6 100%) !important;
  border-color: #7b42f6 !important;
  font-weight: 600 !important;
  box-shadow: 0 3px 10px rgba(123, 66, 246, 0.25) !important;
  transition: all 0.2s ease !important;
}

.export-confirm-btn .el-icon {
  margin-right: 6px !important;
}

.export-confirm-btn:hover {
  background: linear-gradient(135deg, #6d33e6 0%, #5a32a3 100%) !important;
  border-color: #6d33e6 !important;
  transform: translateY(-1px) !important;
  box-shadow: 0 5px 14px rgba(123, 66, 246, 0.35) !important;
}

.export-confirm-btn:active {
  transform: translateY(0) !important;
}

.export-confirm-btn.is-loading {
  background: linear-gradient(135deg, #9f8af0 0%, #8b7ad8 100%) !important;
  border-color: #9f8af0 !important;
  opacity: 0.9 !important;
}

/* ==================== 取消按钮 - 修复悬浮蓝色背景 ==================== */
.el-dialog__footer .el-button:not(.el-button--primary) {
  background-color: #ffffff !important;
  border-color: #dcdfe6 !important;
  color: #606266 !important;
  transition: all 0.2s ease !important;
}

.el-dialog__footer .el-button:not(.el-button--primary):hover {
  background-color: #f5f7fa !important;
  border-color: #7b42f6 !important;
  color: #7b42f6 !important;
}

.el-dialog__footer .el-button:not(.el-button--primary):active {
  background-color: #f0edff !important;
  border-color: #6d33e6 !important;
}
.drawer-header{display:flex;justify-content:space-between;align-items:center;width:100%}

/* ==================== 状态Bug列表抽屉样式 ==================== */
.status-bug-list{padding:0 8px}
.bug-list-container{display:flex;flex-direction:column;gap:12px}
.bug-list-item{background:#fff;border:1px solid rgba(147,112,219,0.15);border-radius:8px;padding:12px 16px;transition:all 0.2s}
.bug-list-item:hover{border-color:rgba(147,112,219,0.3);box-shadow:0 2px 8px rgba(147,112,219,0.08)}
.bug-item-header{display:flex;align-items:center;gap:8px;margin-bottom:6px}
.bug-item-header .bug-serial{font-size:12px;font-weight:600;color:#7c3aed;background:rgba(124,58,237,0.1);padding:2px 8px;border-radius:4px;flex-shrink:0}
.bug-item-header .bug-sev-tag{flex-shrink:0}
.bug-item-header .bug-title{font-size:14px;font-weight:600;color:#333;line-height:1.5;word-break:break-all}
.bug-item-meta{display:flex;gap:12px;flex-wrap:wrap;font-size:12px;color:#999;margin-bottom:6px}
.bug-item-desc{font-size:13px;color:#666;line-height:1.6;word-break:break-all}

/* ==================== 云效同步抽屉样式 ==================== */
.yunxiao-sync-drawer .el-drawer__header {
  margin-bottom: 0;
  padding: 16px 20px;
  border-bottom: 1px solid #e8e8e8;
  font-weight: 800;
}
.yunxiao-drawer-body {
  padding: 20px;
}
.form-tip-inline {
  font-size: 12px;
  color: #909399;
  margin-left: 8px;
}
.max-bugs-row {
  display: flex;
  align-items: center;
}
.yunxiao-drawer-footer {
  display: flex;
  padding: 12px 20px;
}
.yunxiao-drawer-footer .el-button:not(.el-button--primary) {
  background-color: #ffffff;
  border-color: #dcdfe6;
  color: #606266;
}
.yunxiao-drawer-footer .el-button:not(.el-button--primary):hover {
  background-color: #f5f7fa;
  border-color: #7b42f6;
  color: #7b42f6;
}
.yunxiao-drawer-footer .el-button--primary {
  background: linear-gradient(135deg, #7b42f6 0%, #9b6bf5 100%);
  border: none;
  color: #fff;
}
.yunxiao-drawer-footer .el-button--primary:hover {
  background: linear-gradient(135deg, #6a35e0 0%, #8a5ae8 100%);
}
.yunxiao-drawer-footer .el-button--primary.is-disabled {
  background: linear-gradient(135deg, #c4b5e0 0%, #d4c8ec 100%);
  opacity: 0.8;
  cursor: not-allowed;
}

/* ==================== 列表视图样式 - 紫色主题 ==================== */
.filter-bar {
  padding: 20px 24px;
  background: #ffffff;
  border: 1px solid rgba(147, 112, 219, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.filter-bar :deep(.el-input__wrapper) {
  box-shadow: 0 0 0 1px rgba(147, 112, 219, 0.25);
  border-radius: 8px;
  background: #ffffff;
}

.filter-bar :deep(.el-input__wrapper:hover),
.filter-bar :deep(.el-input__wrapper:focus) {
  box-shadow: 0 0 0 1px #7b42f6;
}

.filter-bar-spacer {
  flex: 1;
}

.card-container {
  background: #ffffff;
  border: 1px solid rgba(147, 112, 219, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
  overflow: hidden;
}

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
}

.history-card :deep(.el-table) {
  --el-table-border-color: rgba(147, 112, 219, 0.1);
  --el-table-header-bg-color: #ffffff;
  --el-table-row-hover-bg-color: #f8f7ff;
  border: none;
  border-radius: 8px 8px 0 0;
  overflow: hidden;
  min-height: 200px;
  box-shadow: none;
  transition: all 0.3s ease;
  background-color: transparent !important;
}

.history-card :deep(.el-table__header-wrapper) {
  background-color: #ffffff !important;
}

.history-card :deep(.el-table__header) {
  background-color: #ffffff !important;
}

.history-card :deep(th) {
  background-color: #ffffff !important;
  color: #5a32a3 !important;
  font-weight: 600;
  font-size: 14px;
  border-bottom: 1px solid #e9ecef;
  padding: 0 !important;
  text-align: center;
  transition: all 0.3s ease;
}

.history-card :deep(th:hover) {
  background-color: #ffffff !important;
}

.history-card :deep(th .cell) {
  background-color: #ffffff !important;
  color: #5a32a3 !important;
  font-weight: 600 !important;
  white-space: nowrap !important;
  line-height: 24px !important;
  padding: 16px !important;
}

.history-card :deep(.el-table__body-wrapper) {
  background-color: #ffffff !important;
}

.history-card :deep(.el-table__row) {
  transition: all 0.3s ease;
  background-color: #ffffff !important;
  line-height: 24px;
}

.history-card :deep(.el-table__row:hover) {
  background-color: #f8f7ff !important;
}

.history-card :deep(.el-table__row.el-table__row--striped) {
  background-color: #fafaff !important;
}

.history-card :deep(td) {
  padding: 14px 16px;
  border-bottom: 1px solid #e9ecef;
  color: #333;
  font-size: 14px;
  font-weight: 400;
  line-height: 24px;
  transition: all 0.3s ease;
  vertical-align: middle;
}


.history-card :deep(.el-table__empty-block) {
  padding: 60px 0;
  background: #ffffff !important;
}

.history-card :deep(.el-table__empty-text) {
  color: #666;
  font-size: 14px;
  line-height: 24px;
}

.file-name {
  font-weight: 500;
  color: #333;
}

/* 徽章样式 - 参考 XMindConverter 风格 */
.count-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 24px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
  background: #e6f7ff;
  color: #1890ff;
  white-space: nowrap;
}

.version-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
  background: #f5f3ff;
  color: #7b42f6;
  white-space: nowrap;
  transition: all 0.3s ease;
}

.p0-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 24px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
  background: #fff1f0;
  color: #f5222d;
  white-space: nowrap;
  transition: all 0.3s ease;
}

.p0-badge-zero {
  background: #f5f5f5;
  color: #999;
}

.top-module-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
  background: #f6ffed;
  color: #52c41a;
  white-space: nowrap;
  transition: all 0.3s ease;
}

.time-text {
  color: #333;
  font-size: 13px;
}

.creator-text {
  color: #333;
  font-size: 13px;
}

.action-buttons {
  display: flex;
  gap: 4px;
  justify-content: center;
  align-items: center;
}

.action-buttons .el-button {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  font-weight: 500;
  padding: 4px 10px !important;
  border-radius: 6px;
  transition: all 0.3s ease;
}

.action-buttons .el-button--primary {
  background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%) !important;
  border: none !important;
  color: #ffffff !important;
  font-weight: 600 !important;
}

.action-buttons .el-button--primary:hover {
  background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%) !important;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(123, 66, 246, 0.4);
}

.action-buttons .el-button--danger {
  background: linear-gradient(135deg, #ff4d4f 0%, #f5222d 100%) !important;
  border: none !important;
  color: #ffffff !important;
  font-weight: 600 !important;
}

.action-buttons .el-button--danger:hover {
  background: linear-gradient(135deg, #ff7875 0%, #ff4d4f 100%) !important;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(245, 34, 45, 0.4);
}

.text-gray {
  color: #a898d8;
}

/* ==================== 详情页头部 - 紫色主题 ==================== */
.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  background: #ffffff;
  border: 1px solid rgba(147, 112, 219, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
  margin-bottom: 20px;
}

.detail-header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.detail-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.detail-title h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #5a32a3;
}

.detail-header-actions {
  display: flex;
  gap: 12px;
}

.detail-header-actions .el-button--primary {
  background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
  border-color: #7b42f6;
}

.detail-header-actions .el-button--primary:hover {
  background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%);
  border-color: #6d33e6;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(123, 66, 246, 0.4);
}

/* ==================== 上传对话框样式 ==================== */
.upload-dialog .upload-area {
  width: 100%;
  padding: 40px 0;
}

:deep(.el-dialog__body) {
  padding: 20px;
}

/* ==================== 上传弹窗紫色主题 ==================== */
:deep(.el-dialog__header) {
  background: linear-gradient(135deg, #f8f7ff 0%, #f5f3ff 100%);
  border-bottom: 1px solid rgba(147,112,219,0.15);
  padding: 16px 20px;
  margin-right: 0;
}

:deep(.el-dialog__title) {
  color: #5a32a3;
  font-weight: 600;
  font-size: 16px;
}

:deep(.el-dialog__headerbtn:hover .el-dialog__close) {
  color: #7b42f6;
}

:deep(.el-dialog__footer) {
  border-top: 1px solid rgba(147,112,219,0.1);
  padding: 16px 20px;
}

/* 弹窗内按钮紫色主题 */
:deep(.el-button--primary) {
  background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
  border-color: #7b42f6;
}

:deep(.el-button--primary:hover) {
  background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%);
  border-color: #6d33e6;
}

/* 输入框紫色聚焦效果 */
:deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #7b42f6 inset;
}

:deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px rgba(147,112,219,0.5) inset;
}

/* ==================== 分页组件 - 紫色主题 ==================== */
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
}

.pagination-container :deep(.el-pagination) {
  display: flex;
  align-items: center;
  gap: 4px;
  font-weight: 500;
}

/* 总条数 */
.pagination-container :deep(.el-pagination__total) {
  color: #6b7280;
  font-size: 14px;
  font-weight: 500;
  margin-right: 12px;
}

/* 每页条数选择器 */
.pagination-container :deep(.el-pagination__sizes) {
  margin-right: 12px;
}

.pagination-container :deep(.el-pagination__sizes .el-select .el-input__wrapper) {
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  background: #ffffff;
  box-shadow: none;
}

.pagination-container :deep(.el-pagination__sizes .el-select .el-input__wrapper:hover) {
  border-color: #a78bfa;
  box-shadow: 0 0 0 3px rgba(167, 139, 250, 0.1);
}

.pagination-container :deep(.el-pagination__sizes .el-select .el-input__wrapper.is-focus) {
  border-color: #a78bfa;
  box-shadow: 0 0 0 3px rgba(167, 139, 250, 0.15);
}

.pagination-container :deep(.el-pagination__sizes .el-select .el-input__inner) {
  color: #374151;
  font-weight: 500;
}

/* 上一页/下一页按钮 */
.pagination-container :deep(.el-pagination .btn-prev),
.pagination-container :deep(.el-pagination .btn-next) {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  background: #ffffff;
  color: #6b7280;
  transition: all 0.3s ease;
}

.pagination-container :deep(.el-pagination .btn-prev:hover:not(:disabled)),
.pagination-container :deep(.el-pagination .btn-next:hover:not(:disabled)) {
  background: #f5f3ff;
  border-color: #a78bfa;
  color: #8b5cf6;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(167, 139, 250, 0.2);
}

.pagination-container :deep(.el-pagination .btn-prev:disabled),
.pagination-container :deep(.el-pagination .btn-next:disabled) {
  background: #f5f5f5;
  border-color: #e0e0e0;
  color: #c0c0c0;
}

.pagination-container :deep(.el-pagination .btn-prev .el-icon),
.pagination-container :deep(.el-pagination .btn-next .el-icon) {
  font-size: 14px;
  font-weight: bold;
}

/* 页码按钮 */
.pagination-container :deep(.el-pager) {
  display: flex;
  gap: 8px;
}

.pagination-container :deep(.el-pager li) {
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
}

.pagination-container :deep(.el-pager li:hover:not(.is-active)) {
  background: #f5f3ff;
  border-color: #a78bfa;
  color: #8b5cf6;
  transform: translateY(-1px);
}

.pagination-container :deep(.el-pager li.is-active) {
  background: #f5f3ff;
  border-color: #a78bfa;
  color: #8b5cf6;
  box-shadow: 0 2px 8px rgba(167, 139, 250, 0.2);
}

.pagination-container :deep(.el-pager li.is-active:hover) {
  background: #ede9fe;
  border-color: #8b5cf6;
}

/* 跳转输入框 */
.pagination-container :deep(.el-pagination__jump) {
  color: #6b7280;
  font-weight: 500;
  margin-left: 12px;
}

.pagination-container :deep(.el-pagination__jump .el-input) {
  width: 50px;
  margin: 0 4px;
}

.pagination-container :deep(.el-pagination__jump .el-input__wrapper) {
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  background: #ffffff;
  box-shadow: none;
}

.pagination-container :deep(.el-pagination__jump .el-input__wrapper:hover) {
  border-color: #a78bfa;
  box-shadow: 0 0 0 3px rgba(167, 139, 250, 0.1);
}

.pagination-container :deep(.el-pagination__jump .el-input__wrapper.is-focus) {
  border-color: #a78bfa;
  box-shadow: 0 0 0 3px rgba(167, 139, 250, 0.15);
}

.pagination-container :deep(.el-pagination__jump .el-input__inner) {
  color: #374151;
  font-weight: 500;
  text-align: center;
}

/* ==================== 响应式布局 - 卡片适配 ==================== */
@media (max-width: 1200px) {
  .focus-cards-grid {
    gap: 16px;
  }

  .focus-card {
    padding: 16px;
    min-height: 300px;
    max-height: 380px;
  }

  .focus-name {
    font-size: 16px;
  }
}

@media (max-width: 768px) {
  .focus-cards-grid {
    grid-template-columns: 1fr;
    gap: 16px;
  }

  .focus-card {
    min-height: auto;
    max-height: none;
  }

  .focus-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .focus-badges {
    justify-content: flex-start;
  }

  .focus-body {
    overflow-y: visible;
  }
}

/* ==================== 同步日志抽屉样式 ==================== */
.sync-log-drawer .el-drawer__footer .el-button:not(.el-button--primary) {
  background-color: #ffffff;
  border-color: #dcdfe6;
  color: #606266;
}
.sync-log-drawer .el-drawer__footer .el-button:not(.el-button--primary):hover {
  background-color: #f5f7fa;
  border-color: #7b42f6;
  color: #7b42f6;
}
.sync-log-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
  gap: 12px;
  color: #8b5cf6;
}

.sync-log-content {
  overflow-y: auto;
}

.sync-log-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.sync-log-row .sync-log-card {
  margin-top: 0;
}

.sync-log-card {
  border: 1px solid rgba(139, 92, 246, 0.1);
}

.sync-log-title {
  font-weight: 600;
  color: #7c3aed;
}

.custom-field-keys {
  display: flex;
  flex-wrap: wrap;
  padding: 8px;
}

.custom-fields-preview {
  display: flex;
  flex-wrap: wrap;
  gap: 2px;
}

.first-bug-json {
  background: #1e1e2e;
  color: #cdd6f4;
  padding: 16px;
  border-radius: 8px;
  font-size: 12px;
  max-height: 400px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
