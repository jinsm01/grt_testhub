<template>
  <div class="page-container">
    <!-- 筛选栏 -->
    <div class="filter-bar">
      <el-input
        v-model="searchKeyword"
        placeholder="搜索图谱名称"
        clearable
        @input="handleSearch"
        style="width: 300px;"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
      <div class="filter-bar-spacer"></div>
      <el-button
        v-if="selectedRows.length > 0"
        type="success"
        @click="batchDelete"
      >
        <el-icon><Delete /></el-icon>
        批量删除 ({{ selectedRows.length }})
      </el-button>
      <el-button 
        type="primary" 
        class="select-file-btn"
        @click="showCreateDialog = true"
      >
        <el-icon><Plus /></el-icon>
        创建知识图谱
      </el-button>
    </div>

    <!-- 知识图谱列表 -->
    <div v-if="graphList.length > 0" class="card-container history-card">
      <el-table
        ref="tableRef"
        v-loading="loading"
        :data="graphList"
        style="width: 100%"
        @row-click="handleRowClick"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" header-align="center" align="center" />

        <el-table-column prop="graph_id" label="图谱ID" width="100" header-align="center" align="center" />

        <el-table-column prop="name" label="图谱名称" min-width="200" show-overflow-tooltip header-align="center" align="left" />

        <el-table-column label="状态" width="120" header-align="center" align="center">
          <template #default="{ row }">
            <div class="status-cell">
              <span class="status-badge" :class="row.status">
                {{ row.status_display }}
              </span>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="实体节点" width="90" header-align="center" align="center">
          <template #default="{ row }">
            <span v-if="row.node_count > 0" class="count-text">{{ row.node_count }}</span>
            <span v-else class="text-gray">-</span>
          </template>
        </el-table-column>

        <el-table-column label="关系边" width="90" header-align="center" align="center">
          <template #default="{ row }">
            <span v-if="row.edge_count > 0" class="count-text">{{ row.edge_count }}</span>
            <span v-else class="text-gray">-</span>
          </template>
        </el-table-column>

        <el-table-column label="创建人" width="100" header-align="center" align="center">
          <template #default="{ row }">
            <span v-if="row.created_by_name">{{ row.created_by_name }}</span>
            <span v-else class="text-gray">-</span>
          </template>
        </el-table-column>

        <el-table-column label="创建时间" width="200" header-align="center" align="center">
          <template #default="{ row }">
            <span class="time-text">{{ formatDateTime(row.created_at) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="320" fixed="right" header-align="center" align="center">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button 
                v-if="row.status === 'completed'"
                size="small"
                type="success"
                class="action-btn edit-btn"
                @click.stop="viewDetail(row)"
              >
                <el-icon><View /></el-icon>
                <span>查看</span>
              </el-button>
              <el-button
                size="small"
                type="danger"
                class="action-btn delete-btn"
                @click.stop="confirmDelete(row)"
              >
                <el-icon><Delete /></el-icon>
                <span>删除</span>
              </el-button>
              <!-- 版本下拉菜单 -->
              <div v-if="row.status === 'completed'" class="version-btn-group">
                <el-button
                  size="small"
                  type="primary"
                  class="action-btn version-main-btn"
                  @click.stop="openCreateVersionDialog(row)"
                >
                  <el-icon><CollectionTag /></el-icon>
                  <span>版本</span>
                </el-button>
                <el-dropdown size="small" class="version-dropdown-trigger">
                  <el-button
                    size="small"
                    type="primary"
                    class="action-btn version-arrow-btn"
                  >
                    <el-icon><ArrowDown /></el-icon>
                  </el-button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item @click="openCreateVersionDialog(row)">
                        <el-icon><Plus /></el-icon> 创建版本
                      </el-dropdown-item>
                      <el-dropdown-item @click="openVersionManageDialog(row)">
                        <el-icon><FolderOpened /></el-icon> 版本管理
                      </el-dropdown-item>
                      <el-dropdown-item @click="goToCompare(row)">
                        <el-icon><ScaleToOriginal /></el-icon> 版本对比
                      </el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </div>
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
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else-if="!loading && graphList.length === 0" class="empty-state">
      <div class="empty-icon">
        <el-icon><Share /></el-icon>
      </div>
      <div class="empty-title">暂无知识图谱</div>
      <div class="empty-desc">知识图谱空空如也，创建知识图谱开始构建您的智能知识网络</div>
      <el-button type="primary" size="large" @click="showCreateDialog = true">
        <el-icon><Plus /></el-icon>
        创建知识图谱
      </el-button>
    </div>

    <!-- 知识图谱可视化对话框 -->
    <el-dialog
      v-model="showDetailDialog"
      title="知识图谱可视化"
      width="70%"
      :close-on-click-modal="false"
      class="detail-dialog"
    >
      <div v-if="currentGraph" class="detail-content">
        <!-- 统计卡片已隐藏 -->
        <!--
        <el-row :gutter="20" class="stats-row">
          <el-col :span="6">
            <el-card class="stat-card">
              <div class="stat-icon" style="background: #e6f7ff; color: #1890ff;">
                <el-icon><Share /></el-icon>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ currentGraph.node_count || 0 }}</div>
                <div class="stat-label">实体节点</div>
              </div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card class="stat-card">
              <div class="stat-icon" style="background: #f6ffed; color: #52c41a;">
                <el-icon><Connection /></el-icon>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ currentGraph.edge_count || 0 }}</div>
                <div class="stat-label">关系边</div>
              </div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card class="stat-card">
              <div class="stat-icon" style="background: #fff7e6; color: #fa8c16;">
                <el-icon><Document /></el-icon>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ currentGraph.document_count || 0 }}</div>
                <div class="stat-label">关联文档</div>
              </div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card class="stat-card">
              <div class="stat-icon" style="background: #f9f0ff; color: #722ed1;">
                <el-icon><ChatDotRound /></el-icon>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ queryHistory.length }}</div>
                <div class="stat-label">查询次数</div>
              </div>
            </el-card>
          </el-col>
        </el-row>
        -->

        <!-- 图谱可视化 -->
        <div v-if="currentGraph.status === 'completed'" class="visualization-section">
          <div class="graph-actions" style="display: flex; justify-content: flex-end; margin-bottom: 10px;">
            <el-button text @click="refreshVisualization" :loading="loadingVisualization">
              <el-icon><Refresh /></el-icon> 刷新
            </el-button>
            <el-button text @click="resetZoom">
              <el-icon><ZoomOut /></el-icon> 重置缩放
            </el-button>
          </div>
          <div ref="graphContainer" class="graph-container" style="border: 1px solid #e4e7ed; border-radius: 4px;"></div>
        </div>
      </div>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="showDetailDialog = false">关闭</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 创建知识图谱抽屉 -->
    <el-drawer
      v-model="showCreateDialog"
      title="创建知识图谱"
      size="520px"
      :destroy-on-close="true"
      class="create-graph-drawer"
    >
      <div class="drawer-content">
        <el-form :model="createForm" label-position="top" class="compact-form">
          <!-- 文件上传 -->
          <el-form-item>
            <el-upload
              ref="uploadRef"
              v-model:file-list="createForm.uploadFiles"
              action="#"
              :auto-upload="false"
              :multiple="false"
              :on-change="handleFileChange"
              :on-remove="handleFileRemove"
              accept=".txt,.md,.pdf,.doc,.docx,.xlsx,.xls,.pptx,.ppt,.html,.htm,.csv,.xml,.png,.jpg,.jpeg"
              drag
              class="upload-area compact"
              :show-file-list="false"
            >
              <el-icon class="upload-icon"><UploadFilled /></el-icon>
              <div class="upload-text">
                <span>拖拽文件到此处，或</span>
                <em>点击上传</em>
              </div>
              <div class="upload-formats">
                支持 PDF、Word、Excel、PPT、HTML、Markdown、图片、CSV、XML、TXT（仅限单个文件）
              </div>
            </el-upload>
          </el-form-item>

          <!-- 已选文件列表 -->
          <div v-if="createForm.uploadFiles.length > 0" class="file-list compact">
            <div class="file-items">
              <div v-for="file in createForm.uploadFiles" :key="file.uid" class="file-item">
                <el-icon class="file-icon"><Document /></el-icon>
                <span class="file-name" :title="file.name">{{ file.name }}</span>
                <el-icon class="file-remove" @click="removeFile(file)"><Close /></el-icon>
              </div>
            </div>
          </div>
        </el-form>
      </div>

      <!-- 底部操作栏 -->
      <template #footer>
        <div class="drawer-footer">
          <el-button @click="showCreateDialog = false" size="large">取消</el-button>
          <el-button 
            type="primary" 
            @click="createGraph" 
            :loading="creating"
            size="large"
            :disabled="!canCreate"
          >
            创建并构建
          </el-button>
        </div>
      </template>
    </el-drawer>

    <!-- 构建进度对话框 -->
    <el-dialog
      v-model="showBuildProgress"
      title="构建知识图谱"
      width="480px"
      :close-on-click-modal="false"
      :show-close="false"
      class="build-progress-dialog"
    >
      <div class="build-progress-enhanced">
        <!-- 步骤指示器 -->
        <div class="steps-indicator">
          <div 
            v-for="(step, index) in buildSteps" 
            :key="index"
            class="step-item"
            :class="{ 
              'active': currentStepIndex === index,
              'completed': currentStepIndex > index,
              'pending': currentStepIndex < index
            }"
          >
            <div class="step-icon">
              <el-icon v-if="currentStepIndex > index"><Check /></el-icon>
              <span v-else-if="currentStepIndex === index" class="step-number">{{ index + 1 }}</span>
              <span v-else class="step-number">{{ index + 1 }}</span>
            </div>
            <div class="step-title">{{ step.title }}</div>
            <div v-if="index < buildSteps.length - 1" class="step-line"></div>
          </div>
        </div>

        <!-- 进度条 + 百分比 -->
        <div class="progress-row">
          <el-progress 
            :percentage="buildProgress" 
            :status="buildStatus"
            :stroke-width="12"
            :show-text="false"
            class="build-progress-bar"
          />
          <span class="progress-text">{{ buildProgress }}%</span>
        </div>

        <!-- 状态 + 时间 一行 -->
        <div class="status-row">
          <div class="status-left">
            <el-icon class="status-icon" :class="buildStatus">
              <Loading v-if="buildStatus !== 'success' && buildStatus !== 'exception'" />
              <CircleCheck v-else-if="buildStatus === 'success'" />
              <CircleClose v-else />
            </el-icon>
            <span class="status-label" :class="buildStatus">{{ buildStatusText }}</span>
          </div>
          <div class="status-right" v-if="buildStartTime">
            <el-icon><Clock /></el-icon>
            <span>{{ elapsedTime }}</span>
          </div>
        </div>

        <!-- 当前处理文件 -->
        <div class="file-row" v-if="currentDocument">
          <el-icon><Document /></el-icon>
          <span class="file-name" :title="currentDocument">{{ currentDocument }}</span>
        </div>

        <!-- 预计剩余时间 -->
        <div class="time-estimate" v-if="buildProgress > 0 && buildProgress < 100">
          <el-icon><Timer /></el-icon>
          <span>预计剩余时间: {{ estimatedRemainingTime }}</span>
        </div>

        <!-- 提示信息 -->
        <div class="tips-row" v-if="buildProgress < 100 && buildStatus !== 'exception'">
          <el-icon><InfoFilled /></el-icon>
          <span>{{ currentStepTip }}</span>
        </div>
      </div>
    </el-dialog>

    <!-- 创建版本对话框 -->
    <el-dialog
      v-model="showCreateVersionDialog"
      title="创建知识图谱版本"
      width="500px"
      :close-on-click-modal="false"
    >
      <div v-if="currentGraphForVersion" class="version-dialog-content">
        <div class="current-graph-info" style="margin-bottom: 20px; padding: 12px; background: #f5f7fa; border-radius: 4px;">
          <div style="font-weight: 500; color: #303133; margin-bottom: 4px;">
            <el-icon><Share /></el-icon> 当前图谱: {{ currentGraphForVersion.name }}
          </div>
          <div style="font-size: 13px; color: #606266;">
            实体: {{ currentGraphForVersion.node_count }} | 
            关系: {{ currentGraphForVersion.edge_count }} | 
            文档: {{ currentGraphForVersion.document_count }}
          </div>
        </div>

        <el-form :model="createVersionForm" label-position="top">
          <el-form-item label="版本号" required>
            <el-input
              v-model="createVersionForm.version_number"
              placeholder="例如: V1, V2, 1.0.0"
            />
          </el-form-item>
          <el-form-item label="版本名称">
            <el-input
              v-model="createVersionForm.version_name"
              placeholder="例如: 初始版本, 功能完善版"
            />
          </el-form-item>
          <el-form-item label="版本描述">
            <el-input
              v-model="createVersionForm.description"
              type="textarea"
              :rows="3"
              placeholder="描述这个版本的主要变更内容"
            />
          </el-form-item>
        </el-form>
      </div>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="showCreateVersionDialog = false">取消</el-button>
          <el-button
            type="primary"
            @click="createVersion"
            :loading="creatingVersion"
          >
            创建版本
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 版本管理对话框 -->
    <el-dialog
      v-model="showVersionManageDialog"
      title="版本管理"
      width="700px"
      :close-on-click-modal="false"
    >
      <div v-if="currentGraphForManage" class="version-manage-content">
        <div class="graph-info-header" style="margin-bottom: 20px; padding: 12px; background: #f5f7fa; border-radius: 4px;">
          <div style="font-weight: 500; color: #303133;">
            <el-icon><Share /></el-icon> 当前图谱: {{ currentGraphForManage.name }}
          </div>
          <div style="font-size: 13px; color: #606266; margin-top: 4px;">
            实体: {{ currentGraphForManage.node_count }} | 关系: {{ currentGraphForManage.edge_count }} | 文档: {{ currentGraphForManage.document_count }}
          </div>
        </div>

        <el-table
          v-if="graphVersions.length > 0"
          v-loading="loadingVersions"
          :data="graphVersions"
          style="width: 100%"
          border
        >
          <el-table-column prop="version_number" label="版本号" width="100" />
          <el-table-column prop="version_name" label="版本名称" width="150" show-overflow-tooltip />
          <el-table-column prop="description" label="描述" min-width="280" show-overflow-tooltip />
          <el-table-column label="操作" width="80" fixed="right" align="center">
            <template #default="{ row }">
              <el-button
                type="danger"
                size="small"
                link
                @click="deleteVersion(row)"
              >
                <el-icon><Delete /></el-icon>
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-empty v-if="!loadingVersions && graphVersions.length === 0" description="暂无版本" />
      </div>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="showVersionManageDialog = false">关闭</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch, nextTick, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'
import api from '@/utils/api'
import * as echarts from 'echarts'
import {
  Search, Delete, Plus, View, ScaleToOriginal, UploadFilled,
  Document, Close, Loading, CircleCheck, CircleClose, InfoFilled,
  Refresh, ZoomOut, Share, Clock, CollectionTag, FolderOpened, ArrowDown
} from '@element-plus/icons-vue'

const router = useRouter()

// 状态
const loading = ref(false)
const refreshing = ref(false)
const creating = ref(false)
const projects = ref([])
const selectedProject = ref(null)
const graphList = ref([])
const selectedGraphId = ref(null)
const selectedRows = ref([])
const queryHistory = ref([])
const showCreateDialog = ref(false)
const showBuildProgress = ref(false)
const showDetailDialog = ref(false)
const showCreateVersionDialog = ref(false)
const showVersionManageDialog = ref(false)
const currentGraphForVersion = ref(null)
const currentGraphForManage = ref(null)
const graphVersions = ref([])
const loadingVersions = ref(false)
const createVersionForm = ref({
  version_number: '',
  version_name: '',
  description: ''
})
const creatingVersion = ref(false)
const buildProgress = ref(0)
const buildStatus = ref('')
const buildStatusText = ref('准备中...')
const currentDocument = ref('')
const buildStartTime = ref(null)
const elapsedTime = ref('00:00')
const estimatedRemainingTime = ref('计算中...')

// 构建步骤配置
const buildSteps = [
  { title: '初始化', tip: '正在初始化存储环境...' },
  { title: '提取文本', tip: '正在从文档中提取文本内容...' },
  { title: '分析文档', tip: 'AI正在分析文档结构和语义...' },
  { title: '构建图谱', tip: '正在构建知识图谱节点和关系...' },
  { title: '生成统计', tip: '正在生成图谱统计信息...' },
  { title: '完成', tip: '构建完成！' }
]
const currentStepIndex = ref(0)
const currentStepTip = computed(() => {
  if (currentStepIndex.value < buildSteps.length) {
    return buildSteps[currentStepIndex.value].tip
  }
  return '处理中...'
})

// 计时器
let buildTimer = null

// 格式化时间
const formatDuration = (seconds) => {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = seconds % 60
  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }
  return `${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

// 开始计时
const startBuildTimer = () => {
  buildStartTime.value = Date.now()
  elapsedTime.value = '00:00'
  estimatedRemainingTime.value = '计算中...'
  
  if (buildTimer) clearInterval(buildTimer)
  buildTimer = setInterval(() => {
    const elapsed = Math.floor((Date.now() - buildStartTime.value) / 1000)
    elapsedTime.value = formatDuration(elapsed)
    
    // 计算预计剩余时间
    if (buildProgress.value > 0 && buildProgress.value < 100) {
      const totalEstimated = elapsed / (buildProgress.value / 100)
      const remaining = Math.max(0, Math.floor(totalEstimated - elapsed))
      estimatedRemainingTime.value = formatDuration(remaining)
    }
  }, 1000)
}

// 停止计时
const stopBuildTimer = () => {
  if (buildTimer) {
    clearInterval(buildTimer)
    buildTimer = null
  }
}
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)
const searchKeyword = ref('')

// 表单
const createForm = ref({
  name: '',
  description: '',
  uploadFiles: []
})

// 文件上传相关
const uploadRef = ref(null)

// 可视化相关
const graphContainer = ref(null)
let chartInstance = null
const loadingVisualization = ref(false)
const graphData = ref({ nodes: [], edges: [] })

// 当前图谱
const currentGraph = computed(() => {
  return graphList.value.find(g => g.id === selectedGraphId.value)
})

// 获取可视化数据
const fetchVisualizationData = async () => {
  if (!selectedGraphId.value) return

  loadingVisualization.value = true
  try {
    const response = await api.get(`/requirement-analysis/knowledge-graphs/${selectedGraphId.value}/graph_data/`)
    graphData.value = {
      nodes: response.data.nodes,
      edges: response.data.edges
    }
    await nextTick()
    renderGraph()
  } catch (error) {
    console.error('获取可视化数据失败:', error)
    ElMessage.error('获取可视化数据失败')
  } finally {
    loadingVisualization.value = false
  }
}

// 渲染图谱
const renderGraph = () => {
  if (!graphContainer.value || !graphData.value.nodes.length) return

  // 销毁旧实例
  if (chartInstance) {
    chartInstance.dispose()
  }

  chartInstance = echarts.init(graphContainer.value)

  // 处理节点数据
  const nodes = graphData.value.nodes.map((node, index) => ({
    id: node.id,
    name: node.label || node.id,
    value: node.weight || 1,
    symbolSize: Math.max(20, Math.min(50, (node.weight || 1) * 20)),
    category: node.category || 0,
    itemStyle: {
      color: getNodeColor(node.category)
    }
  }))

  // 处理边数据
  const edges = graphData.value.edges.map(edge => ({
    source: edge.source,
    target: edge.target,
    name: edge.label || '',
    lineStyle: {
      width: Math.max(1, (edge.weight || 1) * 2),
      curveness: 0.2
    }
  }))

  // 获取所有类别
  const categories = Array.from(new Set(graphData.value.nodes.map(n => n.category || 0))).map(cat => ({
    name: `类别 ${cat}`
  }))

  const option = {
    tooltip: {
      formatter: function (x) {
        if (x.dataType === 'node') {
          return `${x.data.name}`
        } else {
          return `${x.data.source} → ${x.data.target}<br/>${x.data.name || ''}`
        }
      }
    },
    series: [{
      type: 'graph',
      layout: 'force',
      data: nodes,
      links: edges,
      categories: categories,
      roam: true,
      label: {
        show: true,
        position: 'right',
        formatter: '{b}'
      },
      lineStyle: {
        color: 'source',
        curveness: 0.3
      },
      emphasis: {
        focus: 'adjacency',
        lineStyle: {
          width: 10
        }
      },
      force: {
        repulsion: 500,
        edgeLength: 150,
        gravity: 0.1
      }
    }]
  }

  chartInstance.setOption(option)
  window.addEventListener('resize', resizeChart)
}

// 获取节点颜色
const getNodeColor = (category) => {
  const colors = [
    '#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de',
    '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc'
  ]
  return colors[(category || 0) % colors.length]
}

// 重置缩放
const resetZoom = () => {
  if (chartInstance) {
    chartInstance.dispatchAction({
      type: 'restore'
    })
  }
}

// 刷新可视化
const refreshVisualization = () => {
  fetchVisualizationData()
}

// 调整图表大小
const resizeChart = () => {
  if (chartInstance) {
    chartInstance.resize()
  }
}

// 组件卸载时清理
onUnmounted(() => {
  if (chartInstance) {
    chartInstance.dispose()
  }
  window.removeEventListener('resize', resizeChart)
})

// 文件变更处理 - 限制单文件
const handleFileChange = (file, fileList) => {
  // 只保留最后一个文件（单文件限制）
  createForm.value.uploadFiles = fileList.slice(-1)
  
  // 自动设置图谱名称为文件名（去掉扩展名）
  if (createForm.value.uploadFiles.length > 0) {
    const fileName = createForm.value.uploadFiles[0].name
    // 去掉扩展名
    createForm.value.name = fileName.replace(/\.[^/.]+$/, '')
  }
}

// 文件移除处理
const handleFileRemove = (file, fileList) => {
  createForm.value.uploadFiles = fileList
}

// 移除文件
const removeFile = (file) => {
  const index = createForm.value.uploadFiles.findIndex(f => f.uid === file.uid)
  if (index > -1) {
    createForm.value.uploadFiles.splice(index, 1)
  }
  // 清空图谱名称
  createForm.value.name = ''
}

// 是否可以创建（只需要有文件即可）
const canCreate = computed(() => {
  return createForm.value.uploadFiles.length > 0
})

// 获取项目列表
const fetchProjects = async () => {
  try {
    const response = await api.get('/projects/')
    projects.value = response.data.results || response.data
  } catch (error) {
    console.error('获取项目列表失败:', error)
    ElMessage.error('获取项目列表失败')
  }
}

// 获取知识图谱列表
const fetchGraphList = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value
    }
    if (searchKeyword.value) {
      params.search = searchKeyword.value
    }
    
    const response = await api.get('/requirement-analysis/knowledge-graphs/', {
      params
    })
    graphList.value = response.data.results || response.data
    total.value = response.data.count || response.data.length
    
    // 默认选择第一个
    if (graphList.value.length > 0 && !selectedGraphId.value) {
      selectedGraphId.value = graphList.value[0].id
    }
  } catch (error) {
    console.error('获取知识图谱列表失败:', error)
    ElMessage.error('获取知识图谱列表失败')
  } finally {
    loading.value = false
  }
}

// 获取查询历史
const fetchQueryHistory = async () => {
  if (!selectedGraphId.value) return
  
  try {
    const response = await api.get(`/requirement-analysis/knowledge-graphs/${selectedGraphId.value}/query_history/`)
    queryHistory.value = response.data
  } catch (error) {
    console.error('获取查询历史失败:', error)
  }
}

// 项目变更
const handleProjectChange = () => {
  selectedGraphId.value = null
  graphList.value = []
  queryHistory.value = []
  currentPage.value = 1
  fetchGraphList()
}

// 表格行点击
const handleRowClick = (row) => {
  selectedGraphId.value = row.id
}

// 选择变化
const handleSelectionChange = (selection) => {
  selectedRows.value = selection
}

// 批量删除
const batchDelete = async () => {
  if (selectedRows.value.length === 0) {
    ElMessage.warning('请至少选择一条记录')
    return
  }

  const names = selectedRows.value.map(row => row.name).join('、')

  ElMessageBox.confirm(
    `确定要删除选中的 ${selectedRows.value.length} 个知识图谱吗？\n\n${names}\n\n删除后将无法恢复。`,
    '确认批量删除',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      const ids = selectedRows.value.map(row => row.id)
      await api.post('/requirement-analysis/knowledge-graphs/batch_delete/', { ids })
      ElMessage.success('批量删除成功')
      selectedRows.value = []
      fetchGraphList()
    } catch (error) {
      console.error('批量删除失败:', error)
      const errorMsg = error.response?.data?.error || '批量删除失败'
      ElMessage.error(errorMsg)
    }
  }).catch(() => {})
}

// 查看详情 - 在当前页打开可视化
const viewDetail = (row) => {
  router.push(`/ai-assistant/knowledge-graph/visualization/${row.id}`)
}

// 打开创建版本对话框
const openCreateVersionDialog = (row) => {
  currentGraphForVersion.value = row
  createVersionForm.value = {
    version_number: '',
    version_name: '',
    description: ''
  }
  showCreateVersionDialog.value = true
}

// 创建版本
const createVersion = async () => {
  if (!createVersionForm.value.version_number) {
    ElMessage.warning('请输入版本号')
    return
  }

  creatingVersion.value = true
  try {
    const response = await api.post(`/requirement-analysis/knowledge-graphs/${currentGraphForVersion.value.id}/create_version/`, {
      version_number: createVersionForm.value.version_number,
      version_name: createVersionForm.value.version_name,
      description: createVersionForm.value.description
    })

    if (response.data.success) {
      ElMessage.success(`版本 ${createVersionForm.value.version_number} 创建成功`)
      showCreateVersionDialog.value = false
      createVersionForm.value = { version_number: '', version_name: '', description: '' }
    } else {
      ElMessage.error(response.data.error || '创建失败')
    }
  } catch (error) {
    console.error('创建版本失败:', error)
    ElMessage.error('创建版本失败')
  } finally {
    creatingVersion.value = false
  }
}

// 打开版本管理对话框
const openVersionManageDialog = (row) => {
  currentGraphForManage.value = row
  showVersionManageDialog.value = true
  fetchGraphVersions(row.id)
}

// 获取图谱版本列表
const fetchGraphVersions = async (graphId) => {
  loadingVersions.value = true
  try {
    const response = await api.get(`/requirement-analysis/knowledge-graphs/${graphId}/versions/`)
    graphVersions.value = response.data
  } catch (error) {
    console.error('获取版本列表失败:', error)
    ElMessage.error('获取版本列表失败')
    graphVersions.value = []
  } finally {
    loadingVersions.value = false
  }
}

// 删除版本
const deleteVersion = async (version) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除版本 ${version.version_number} 吗？此操作不可恢复。`,
      '确认删除',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await api.delete(`/requirement-analysis/knowledge-graphs/${currentGraphForManage.value.id}/versions/${version.id}/`)
    ElMessage.success('版本删除成功')
    await fetchGraphVersions(currentGraphForManage.value.id)
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除版本失败:', error)
      ElMessage.error('删除版本失败')
    }
  }
}

// 搜索处理
const handleSearch = () => {
  currentPage.value = 1
  fetchGraphList()
}

// 分页处理
const handleSizeChange = (val) => {
  pageSize.value = val
  fetchGraphList()
}

const handleCurrentChange = (val) => {
  currentPage.value = val
  fetchGraphList()
}

// 创建知识图谱
const createGraph = async () => {
  // 验证数据源
  if (createForm.value.uploadFiles.length === 0) {
    ElMessage.warning('请至少上传一个文件')
    return
  }
  
  // 如果没有名称，使用文件名
  if (!createForm.value.name.trim()) {
    const fileName = createForm.value.uploadFiles[0].name
    createForm.value.name = fileName.replace(/\.[^/.]+$/, '')
  }

  creating.value = true
  try {
    // 上传文件并创建图谱
    const formData = new FormData()
    formData.append('name', createForm.value.name)
    formData.append('description', createForm.value.description)
    formData.append('is_public', 'true')
    formData.append('public_access_level', 'read')
    if (selectedProject.value) {
      formData.append('project', selectedProject.value)
    }

    // 添加文件
    createForm.value.uploadFiles.forEach(file => {
      formData.append('files', file.raw)
    })

    const uploadResponse = await api.post(
      '/requirement-analysis/knowledge-graphs/upload-and-create/',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      }
    )

    const graphId = uploadResponse.data.id
    const documentIds = uploadResponse.data.document_ids
    
    // 2. 启动构建任务
    showCreateDialog.value = false
    showBuildProgress.value = true
    buildProgress.value = 0
    buildStatus.value = ''
    buildStatusText.value = '正在启动构建任务...'
    
    // 开始计时
    startBuildTimer()
    
    const buildResponse = await api.post(`/requirement-analysis/knowledge-graphs/${graphId}/build/`, {
      document_ids: documentIds
    })
    
    const taskId = buildResponse.data.task_id
    
    // 3. 轮询构建进度
    pollBuildProgress(taskId, graphId)
    
  } catch (error) {
    console.error('创建知识图谱失败:', error)
    ElMessage.error('创建知识图谱失败')
    creating.value = false
  }
}

// 根据进度更新当前步骤
const updateStepByProgress = (progress) => {
  if (progress < 10) {
    currentStepIndex.value = 0  // 初始化
  } else if (progress < 30) {
    currentStepIndex.value = 1  // 提取文本
  } else if (progress < 70) {
    currentStepIndex.value = 2  // 分析文档
  } else if (progress < 85) {
    currentStepIndex.value = 3  // 构建图谱
  } else if (progress < 100) {
    currentStepIndex.value = 4  // 生成统计
  } else {
    currentStepIndex.value = 5  // 完成
  }
}

// 轮询构建进度
const pollBuildProgress = async (taskId, graphId) => {
  const checkProgress = async () => {
    try {
      const response = await api.get(`/requirement-analysis/knowledge-graphs/build-tasks/${taskId}/status/`)
      const task = response.data
      
      buildProgress.value = task.progress
      currentDocument.value = task.current_document
      
      // 更新当前步骤
      updateStepByProgress(task.progress)
      
      // 根据进度更新状态文本
      if (task.progress < 10) {
        buildStatusText.value = '正在初始化...'
      } else if (task.progress < 30) {
        buildStatusText.value = '正在提取文档内容...'
      } else if (task.progress < 70) {
        buildStatusText.value = 'AI正在分析文档...'
      } else if (task.progress < 85) {
        buildStatusText.value = '正在构建知识图谱...'
      } else if (task.progress < 100) {
        buildStatusText.value = '正在生成统计信息...'
      }
      
      if (task.status === 'completed') {
        buildProgress.value = 100
        currentStepIndex.value = 5
        buildStatus.value = 'success'
        buildStatusText.value = '构建完成！'
        stopBuildTimer()
        ElMessage.success('知识图谱构建成功')
        
        setTimeout(() => {
          showBuildProgress.value = false
          fetchGraphList()
        }, 1500)
        return
      } else if (task.status === 'failed') {
        buildStatus.value = 'exception'
        buildStatusText.value = `构建失败: ${task.error_message}`
        stopBuildTimer()
        ElMessage.error('知识图谱构建失败')
        creating.value = false
        return
      } else {
        setTimeout(checkProgress, 2000)
      }
    } catch (error) {
      console.error('获取构建进度失败:', error)
      buildStatusText.value = '获取进度失败，请刷新页面查看'
      creating.value = false
    }
  }
  
  checkProgress()
}

// 删除图谱
const confirmDelete = (row) => {
  ElMessageBox.confirm(
    `确定要删除知识图谱「${row.name}」吗？删除后将无法恢复。`,
    '确认删除',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      await api.delete(`/requirement-analysis/knowledge-graphs/${row.id}/`)
      ElMessage.success('删除成功')
      if (selectedGraphId.value === row.id) {
        selectedGraphId.value = null
      }
      fetchGraphList()
    } catch (error) {
      console.error('删除失败:', error)
      const errorMsg = error.response?.data?.error || '删除失败'
      ElMessage.error(errorMsg)
    }
  })
}

// 跳转到版本对比
const goToCompare = (row) => {
  router.push({
    name: 'KnowledgeGraphCompare',
    query: { graph_id: row.id }
  })
}

// 获取状态类型
const getStatusType = (status) => {
  const typeMap = {
    'pending': 'info',
    'building': 'warning',
    'completed': 'success',
    'failed': 'danger'
  }
  return typeMap[status] || 'info'
}

// 格式化日期时间
const formatDateTime = (date) => {
  if (!date) return '-'
  const d = new Date(date)
  return d.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  }).replace(/\//g, '-')
}

onMounted(() => {
  fetchProjects()
  fetchGraphList()
})
</script>

<style lang="scss" scoped>
.page-container {
  padding: 24px;
  min-height: calc(100vh - 60px);
  background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%);
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.page-header {
  .page-title {
    margin: 0 0 8px 0;
    font-size: 20px;
    font-weight: 600;
    color: #5a32a3;
  }
  .subtitle {
    margin: 0;
    color: #909399;
    font-size: 14px;
  }
}

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

.section-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 16px;
  padding-left: 10px;
  border-left: 4px solid #7b42f6;
  color: #5a32a3;
  display: flex;
  align-items: center;
  gap: 8px;
}

// 筛选栏
.filter-bar {
  padding: 20px 24px;
  background: #ffffff;
  border: 1px solid rgba(147, 112, 219, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
  display: flex;
  align-items: center;
  gap: 2px;

  :deep(.el-input__wrapper) {
    box-shadow: 0 0 0 1px rgba(147, 112, 219, 0.25);
    border-radius: 8px;
    background: #ffffff;

    &:hover,
    &:focus {
      box-shadow: 0 0 0 1px #7b42f6;
    }
  }

  .filter-bar-spacer {
    flex: 1;
  }

  // 按钮样式
  .select-file-btn {
    background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
    border: none;
    font-weight: 600;
    padding: 10px 20px;

    .el-icon {
      margin-right: 4px;
    }

    &:hover {
      background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%);
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(123, 66, 246, 0.4);
    }

    &:disabled {
      background: #d1d5db;
      transform: none;
      box-shadow: none;
    }
  }
}

// 历史记录样式
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

  .el-table {
    border: none;
    border-radius: 8px 8px 0 0;
    overflow: hidden;
    min-height: 200px;
    box-shadow: none;
    transition: all 0.3s ease;
    background-color: transparent !important;

    /* 覆盖 Element Plus 默认主题变量 */
    --el-color-primary: #7b42f6;
    --el-color-primary-light-3: #9370db;
    --el-color-primary-light-5: #a888e0;
    --el-color-primary-light-7: #c2a9f3;
    --el-color-primary-light-9: #f8f7ff;
    --el-border-color: #e4e7ed;
    --el-border-color-light: #e4e7ed;
    --el-fill-color-light: #ffffff;
    --el-fill-color-blank: #ffffff;
    --el-text-color-primary: #303133;
    --el-text-color-regular: #606266;
    --el-text-color-secondary: #909399;
    --el-table-header-bg-color: #ffffff;
    --el-table-row-hover-bg-color: #f8f7ff;
    --el-table-stripe-bg-color: #ffffff;

    &::before {
      display: none;
    }

    // 表头
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
      border-bottom: 1px solid #e4e7ed;
      padding: 0 !important;
      text-align: center;
      transition: all 0.3s ease;

      &:hover {
        background-color: #ffffff !important;
      }
    }

    :deep(th .cell) {
      background-color: #ffffff !important;
      color: #5a32a3 !important;
      font-weight: 600 !important;
      white-space: nowrap !important;
      line-height: 24px !important;
      padding: 16px !important;
      display: flex;
      align-items: center;
      justify-content: center;
      height: 100%;
    }

    :deep(.el-table__body-wrapper) {
      background-color: #ffffff !important;
    }

    :deep(.el-table__row) {
      transition: all 0.3s ease;
      background-color: #ffffff !important;
      line-height: 24px;
      cursor: pointer;

      &:hover {
        background-color: #f8f7ff !important;
      }

      &.el-table__row--striped {
        background-color: #ffffff !important;
      }
    }

    :deep(td) {
      padding: 14px 16px;
      border-bottom: 1px solid #e4e7ed;
      color: #303133;
      font-size: 14px;
      font-weight: 400;
      line-height: 24px;
      transition: all 0.3s ease;
      vertical-align: middle;
    }

    // 修复复选框垂直对齐
    :deep(.el-checkbox) {
      display: inline-flex;
      align-items: center;
      justify-content: center;
    }

    :deep(.el-checkbox__input) {
      display: inline-flex;
      align-items: center;
      justify-content: center;
    }

    // 修复表头复选框对齐 - 针对表头第一列
    :deep(th:first-child .cell) {
      padding: 0 !important;
      line-height: 56px !important;
    }

    // 修复内容区域复选框对齐 - 针对内容第一列
    :deep(td:first-child) {
      padding: 0 !important;
      text-align: center;
    }

    :deep(td:first-child .cell) {
      padding: 0 !important;
      line-height: 52px !important;
    }

    // 空状态
    :deep(.el-table__empty-block) {
      padding: 60px 0;
      background: #ffffff !important;

      :deep(.el-table__empty-text) {
        color: #909399;
        font-size: 14px;
        line-height: 24px;
      }
    }

    // 修复固定列
    :deep(.el-table__fixed-right) {
      background-color: #ffffff !important;
      height: 100% !important;
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

  // 状态单元格
  .status-cell {
    display: flex;
    align-items: center;
    justify-content: center;
  }

  // 状态标签样式
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

    &.pending {
      background: #f4f4f5;
      color: #909399;
    }

    &.building {
      background: #fdf6ec;
      color: #e6a23c;
    }

    &.completed {
      background: #f6ffed;
      color: #52c41a;
    }

    &.failed {
      background: #fff1f0;
      color: #f5222d;
    }
  }

  // 计数标签样式
  .count-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 44px;
    height: 24px;
    border-radius: 4px;
    font-size: 13px;
    font-weight: 500;
    white-space: nowrap;

    // 实体节点 - 蓝色
    &.count-badge-node {
      background: #e6f7ff;
      color: #1890ff;
    }

    // 关系边 - 紫色
    &.count-badge-edge {
      background: #f9f0ff;
      color: #722ed1;
    }

    // 关联文档 - 橙色
    &.count-badge-doc {
      background: #fff7e6;
      color: #fa8c16;
    }
  }

  // 时间文本样式
  .time-text {
    color: #909399;
    font-size: 14px;
    white-space: nowrap;
  }

  .text-gray {
    color: #909399;
  }

  // 计数文本样式
  .count-text {
    font-weight: 500;
    color: #303133;
  }

  // 图谱名称链接样式
  .graph-name-link {
    font-weight: 500;
    color: #7b42f6;

    &:hover {
      color: #5a32a3;
    }
  }

  .graph-name {
    font-weight: 500;
    color: #303133;
    display: inline-block;
    width: 100%;
    text-align: center;
  }

  .graph-id {
    font-family: 'Courier New', monospace;
    font-size: 12px;
    color: #7b42f6;
    background: #f5f3ff;
    padding: 2px 6px;
    border-radius: 4px;
  }
}

// 版本按钮组样式
.version-btn-group {
  display: flex;
  align-items: center;
  margin-left: 12px;

  .version-main-btn {
    background: linear-gradient(135deg, #9f7aea 0%, #7c3aed 100%) !important;
    border: none !important;
    color: #ffffff !important;
    border-top-right-radius: 0 !important;
    border-bottom-right-radius: 0 !important;
    border-right: 1px solid rgba(255, 255, 255, 0.3) !important;
    margin-right: 0 !important;

    &:hover {
      box-shadow: 0 4px 12px rgba(159, 122, 234, 0.4);
    }
  }

  .version-dropdown-trigger {
    margin-right: 0 !important;

    .version-arrow-btn {
      background: linear-gradient(135deg, #9f7aea 0%, #7c3aed 100%) !important;
      border: none !important;
      border-left: 1px solid rgba(255, 255, 255, 0.3) !important;
      color: #ffffff !important;
      border-top-left-radius: 0 !important;
      border-bottom-left-radius: 0 !important;
      padding: 4px 6px !important;
      margin-left: 0 !important;
      margin-right: 0 !important;
      outline: none !important;

      &:hover,
      &:focus,
      &:active {
        background: linear-gradient(135deg, #9f7aea 0%, #7c3aed 100%) !important;
        border: none !important;
        border-left: 1px solid rgba(255, 255, 255, 0.3) !important;
        box-shadow: 0 4px 12px rgba(159, 122, 234, 0.4);
        outline: none !important;
      }

      .el-icon {
        margin-right: 0 !important;
      }
    }
  }
}

// 操作按钮样式
.page-container {
  .action-buttons {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 8px;
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

    &.edit-btn {
      background: linear-gradient(135deg, #52c41a 0%, #389e0d 100%) !important;
      border: none !important;
      color: #ffffff !important;
      font-weight: 600 !important;

      &:hover {
        background: linear-gradient(135deg, #73d13d 0%, #52c41a 100%) !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(82, 196, 26, 0.4);
      }
    }

    &.run-btn {
      background: linear-gradient(135deg, #52c41a 0%, #389e0d 100%) !important;
      border: none !important;
      color: #ffffff !important;
      font-weight: 600 !important;

      &:hover {
        background: linear-gradient(135deg, #73d13d 0%, #52c41a 100%) !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(82, 196, 26, 0.4);
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

  /* 定义主题变量 */
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
  --el-fill-color-light: #f5f3ff;

  :deep(.el-pagination) {
    display: flex;
    align-items: center;
    gap: 4px;
    font-weight: 500;

    .el-pagination__total {
      color: #6b7280;
      font-size: 14px;
      font-weight: 500;
      margin-right: 12px;
    }

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

// 详情对话框样式
.detail-dialog {
  :deep(.el-dialog__body) {
    max-height: 80vh;
    overflow-y: auto;
    padding: 24px;
  }
}

.detail-content {
  .detail-section {
    margin-bottom: 28px;

    &:last-child {
      margin-bottom: 0;
    }
  }

  // 统计卡片
  .stats-row {
    margin-bottom: 24px;
  }

  .stat-card {
    display: flex;
    align-items: center;
    padding: 20px;
  }

  .stat-icon {
    width: 60px;
    height: 60px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 28px;
    margin-right: 16px;
  }

  .stat-content {
    flex: 1;
  }

  .stat-value {
    font-size: 32px;
    font-weight: bold;
    color: #303133;
    line-height: 1;
    margin-bottom: 8px;
  }

  .stat-label {
    font-size: 14px;
    color: #909399;
  }

  // 可视化
  .visualization-section {
    margin-top: 24px;
  }

  .graph-card {
    height: 500px;
  }

  .graph-container {
    width: 100%;
    height: 400px;
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .header-actions {
    display: flex;
    gap: 8px;
  }
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

// 空状态
.empty-state {
  background: #ffffff;
  border: 1px solid rgba(147, 112, 219, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
  padding: 80px 20px;
  text-align: center;

  .empty-icon {
    font-size: 64px;
    color: #c4b5fd;
    margin-bottom: 20px;

    .el-icon {
      font-size: 64px;
    }
  }

  .empty-title {
    font-size: 18px;
    font-weight: 600;
    color: #303133;
    margin-bottom: 8px;
  }

  .empty-desc {
    font-size: 14px;
    color: #909399;
    margin-bottom: 24px;
  }

  .el-button {
    .el-icon {
      margin-right: 4px;
    }
  }
}

// 抽屉样式
.create-graph-drawer :deep(.el-drawer__header) {
  margin-bottom: 0;
  padding: 20px 24px;
  border-bottom: 1px solid #e4e7ed;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.create-graph-drawer :deep(.el-drawer__body) {
  padding: 0;
  background: #f5f7fa;
}

.create-graph-drawer :deep(.el-drawer__footer) {
  padding: 16px 24px;
  background: #ffffff;
  border-top: 1px solid #e4e7ed;
}

.drawer-footer {
  width: 100%;
  display: flex;
  justify-content: flex-start;
  gap: 2px;

  .el-button {
    min-width: 100px;
    border-radius: 6px;
    font-weight: 500;

    &:not(.el-button--primary) {
      border: 1px solid #dcdfe6;
      color: #606266;

      &:hover {
        color: #7b42f6;
        border-color: #c4b5fd;
        background: #f5f3ff;
      }
    }

    &--primary {
      background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
      border: none;
      box-shadow: 0 2px 8px rgba(123, 66, 246, 0.3);

      &:hover {
        background: linear-gradient(135deg, #6a3ad9 0%, #4a2a8a 100%);
        box-shadow: 0 4px 12px rgba(123, 66, 246, 0.4);
      }

      &:disabled {
        background: linear-gradient(135deg, #c4b5fd 0%, #a78bfa 100%);
        box-shadow: none;
      }
    }
  }
}

.drawer-content {
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.section-card {
  background: #ffffff;
  border-radius: 12px;
  padding: 20px;
}

.data-source-tabs {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;

  .tab-item {
    flex: 1;
    padding: 12px 20px;
    border: 2px solid #e4e7ed;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    cursor: pointer;
    transition: all 0.3s ease;
    font-weight: 500;
    color: #606266;

    &:hover {
      border-color: #c4b5fd;
      background: #f5f3ff;
    }

    &.active {
      border-color: #7b42f6;
      background: #f5f3ff;
      color: #5a32a3;
    }
  }
}

.source-content {
  .empty-tip {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 40px;
    color: #909399;
    gap: 12px;
  }

  .doc-checkbox-group {
    .doc-list {
      max-height: 300px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 12px;

      .doc-checkbox {
        padding: 12px 16px;
        border: 1px solid #e4e7ed;
        border-radius: 8px;
        transition: all 0.3s ease;

        &:hover {
          border-color: #c4b5fd;
          background: #f5f3ff;
        }

        .doc-item {
          display: flex;
          align-items: center;
          gap: 8px;

          .doc-name {
            flex: 1;
            font-weight: 500;
            color: #303133;
          }
        }
      }
    }
  }

  .selected-count {
    margin-top: 16px;
    padding: 12px;
    background: #f5f3ff;
    border-radius: 8px;
    color: #5a32a3;
    font-weight: 500;
    text-align: center;
  }
}

.upload-area {
  width: 100%;

  :deep(.el-upload-dragger) {
    width: 100%;
    border: 2px dashed #c4b5fd;
    border-radius: 12px;
    background: #f8f7ff;
    transition: all 0.3s ease;

    &:hover {
      border-color: #7b42f6;
      background: #ede9fe;
    }
  }

  .upload-icon {
    font-size: 48px;
    color: #7b42f6;
    margin-bottom: 16px;
  }

  .upload-text {
    font-size: 16px;
    color: #303133;

    em {
      color: #7b42f6;
      font-weight: 600;
      font-style: normal;
    }
  }

  .upload-tip {
    color: #909399;
    font-size: 14px;
  }
}

.file-list {
  margin-top: 20px;

  .file-list-title {
    font-weight: 600;
    color: #303133;
    margin-bottom: 12px;
  }

  .file-items {
    display: flex;
    flex-direction: column;
    gap: 12px;

    .file-item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px 16px;
      background: #f8f7ff;
      border: 1px solid #e4e7ed;
      border-radius: 8px;

      .file-name {
        flex: 1;
        font-weight: 500;
        color: #303133;
      }

      .file-remove {
        color: #f56c6c;
        cursor: pointer;
        transition: all 0.2s ease;

        &:hover {
          color: #f5222d;
        }
      }
    }
  }
}

.form-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
  padding: 10px 14px;
  background: #f0f9eb;
  border-radius: 6px;
  font-size: 13px;
  color: #67c23a;
}

// 增强版构建进度弹窗
.build-progress-enhanced {
  padding: 8px 4px;

  // 步骤指示器
  .steps-indicator {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    margin-bottom: 24px;
    padding: 0 8px;

    .step-item {
      display: flex;
      flex-direction: column;
      align-items: center;
      position: relative;
      flex: 1;

      .step-icon {
        width: 32px;
        height: 32px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 14px;
        margin-bottom: 6px;
        transition: all 0.3s ease;

        .step-number {
          font-weight: 600;
          font-size: 12px;
        }
      }

      .step-title {
        font-size: 11px;
        color: #9ca3af;
        text-align: center;
        white-space: nowrap;
        transition: all 0.3s ease;
      }

      .step-line {
        position: absolute;
        top: 16px;
        right: -50%;
        width: 100%;
        height: 2px;
        background: #e5e7eb;
        z-index: 0;
      }

      // 已完成状态
      &.completed {
        .step-icon {
          background: #22c55e;
          color: white;
        }

        .step-title {
          color: #22c55e;
        }
      }

      // 进行中状态
      &.active {
        .step-icon {
          background: #7b42f6;
          color: white;
          box-shadow: 0 0 0 4px rgba(123, 66, 246, 0.2);
          animation: pulse 2s infinite;
        }

        .step-title {
          color: #7b42f6;
          font-weight: 600;
        }
      }

      // 待处理状态
      &.pending {
        .step-icon {
          background: #f3f4f6;
          color: #9ca3af;
          border: 2px solid #e5e7eb;
        }
      }
    }
  }

  // 进度条行
  .progress-row {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 16px;

    .build-progress-bar {
      flex: 1;

      :deep(.el-progress-bar__outer) {
        background-color: #f3f4f6;
        border-radius: 8px;
      }

      :deep(.el-progress-bar__inner) {
        border-radius: 8px;
        background: linear-gradient(90deg, #7b42f6 0%, #a855f7 100%);
        transition: width 0.5s ease;
      }
    }

    .progress-text {
      font-size: 18px;
      font-weight: 600;
      color: #7b42f6;
      min-width: 45px;
      text-align: right;
    }
  }

  // 状态行：状态 + 时间
  .status-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;

    .status-left {
      display: flex;
      align-items: center;
      gap: 8px;

      .status-icon {
        font-size: 18px;

        &.success {
          color: #22c55e;
        }

        &.exception {
          color: #ef4444;
        }

        &:not(.success):not(.exception) {
          color: #7b42f6;
          animation: rotating 1.5s linear infinite;
        }
      }

      .status-label {
        font-size: 14px;
        font-weight: 500;
        color: #374151;

        &.success {
          color: #22c55e;
        }

        &.exception {
          color: #ef4444;
        }
      }
    }

    .status-right {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 13px;
      color: #6b7280;
      background: #f9fafb;
      padding: 4px 10px;
      border-radius: 6px;

      .el-icon {
        font-size: 14px;
        color: #9ca3af;
      }
    }
  }

  // 文件行
  .file-row {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 12px;
    background: #f9fafb;
    border-radius: 8px;
    margin-bottom: 12px;

    .el-icon {
      font-size: 16px;
      color: #7b42f6;
      flex-shrink: 0;
    }

    .file-name {
      font-size: 13px;
      color: #4b5563;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  // 预计剩余时间
  .time-estimate {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    color: #6b7280;
    margin-bottom: 12px;
    padding: 6px 10px;
    background: #fef3c7;
    border-radius: 6px;

    .el-icon {
      font-size: 14px;
      color: #f59e0b;
    }
  }

  // 提示行
  .tips-row {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    font-size: 13px;
    color: #6b7280;
    padding: 10px 12px;
    background: #eff6ff;
    border-radius: 8px;
    line-height: 1.5;

    .el-icon {
      font-size: 16px;
      color: #3b82f6;
      flex-shrink: 0;
      margin-top: 1px;
    }
  }
}

// 脉冲动画
@keyframes pulse {
  0%, 100% {
    box-shadow: 0 0 0 4px rgba(123, 66, 246, 0.2);
  }
  50% {
    box-shadow: 0 0 0 8px rgba(123, 66, 246, 0.1);
  }
}

// 旋转动画
@keyframes rotating {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

// 构建进度弹窗样式
.build-progress-dialog {
  :deep(.el-dialog__header) {
    padding: 16px 20px;
    margin-right: 0;
    border-bottom: 1px solid #f3f4f6;

    .el-dialog__title {
      font-size: 16px;
      font-weight: 600;
      color: #1f2937;
    }
  }

  :deep(.el-dialog__body) {
    padding: 20px;
  }
}

.build-status-text {
  margin-top: 16px;
  font-size: 16px;
  color: #606266;
}

.build-detail {
  margin-top: 8px;
  font-size: 14px;
  color: #909399;
}

// 简洁表单样式
.compact-form {
  .el-form-item {
    margin-bottom: 20px;

    &:last-child {
      margin-bottom: 0;
    }

    .el-form-item__label {
      font-size: 16px;
      font-weight: 700;
      color: #000000;
      padding-bottom: 12px;
      letter-spacing: 0.5px;

      &::before {
        color: #ff4d4f;
        font-weight: 700;
        font-size: 18px;
        margin-right: 4px;
      }
    }
  }

  // 紧凑上传区域
  .upload-area.compact {
    border: none;
    padding: 0;

    .el-upload {
      display: block;
    }

    .el-upload-dragger {
      border: 2px dashed #dcdfe6;
      border-radius: 8px;
      padding: 24px 20px;
      background: transparent;
      transition: all 0.3s ease;

      &:hover {
        border-color: #7b42f6;
        background: #faf8ff;
      }
    }

    .upload-icon {
      font-size: 32px;
      color: #7b42f6;
      margin-bottom: 8px;
    }

    .upload-text {
      font-size: 14px;
      color: #606266;
      margin-bottom: 4px;

      em {
        color: #7b42f6;
        font-style: normal;
        font-weight: 500;
        cursor: pointer;

        &:hover {
          text-decoration: underline;
        }
      }
    }

    .upload-formats {
      font-size: 12px;
      color: #909399;
    }
  }

  // 紧凑文件列表
  .file-list.compact {
    margin-top: 12px;

    .file-items {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .file-item {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      background: #f5f7fa;
      border-radius: 6px;
      font-size: 13px;

      .file-icon {
        font-size: 16px;
        color: #7b42f6;
        flex-shrink: 0;
      }

      .file-name {
        flex: 1;
        color: #303133;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .file-remove {
        font-size: 14px;
        color: #909399;
        cursor: pointer;
        flex-shrink: 0;

        &:hover {
          color: #f56c6c;
        }
      }
    }
  }
}
</style>
