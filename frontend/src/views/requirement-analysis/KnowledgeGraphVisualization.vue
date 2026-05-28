<template>
  <div ref="pageContainerRef" class="page-container" :class="{ 'is-fullscreen': isFullscreen }">
    <!-- 顶部导航栏 -->
    <div class="filter-bar">
      <!-- 搜索框 -->
      <div class="search-box" v-if="graphStatus === 'completed' && !loading" v-click-outside="closeSearchResults">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索节点名称"
          clearable
          @input="handleSearch"
          @clear="clearSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <div v-if="showSearchResults && searchResults.length > 0" class="search-results">
          <div class="search-results-header">
            找到 {{ searchResults.length }} 个节点
          </div>
          <div
            v-for="(node, index) in searchResults"
            :key="node.id"
            class="search-result-item"
            :class="{ active: currentSearchIndex === index }"
            @click="locateNode(node, index)"
          >
            <span class="node-dot" :style="{ backgroundColor: node.itemStyle?.color }"></span>
            <span class="node-name">{{ node.name }}</span>
          </div>
        </div>
      </div>
      <div class="filter-bar-spacer"></div>
      <div class="header-actions">
        <el-button @click="refreshVisualization" :loading="loading">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
        <el-button @click="resetZoom">
          <el-icon><ZoomOut /></el-icon>
          重置缩放
        </el-button>
        <el-button @click="toggleFullscreen">
          <el-icon><FullScreen /></el-icon>
          {{ isFullscreen ? '退出全屏' : '全屏' }}
        </el-button>

      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-container">
      <el-skeleton :rows="10" animated />
    </div>

    <!-- 错误状态 -->
    <div v-else-if="error" class="error-container">
      <el-empty description="加载失败">
        <el-button @click="loadGraphData">重新加载</el-button>
      </el-empty>
    </div>

    <!-- 图谱可视化 -->
    <div v-else-if="graphStatus === 'completed'" class="card-container">
      <div ref="graphContainer" class="graph-canvas"></div>
    </div>

    <!-- 未构建完成状态 -->
    <div v-else class="empty-container">
      <el-empty :description="statusText || '暂无数据'">
        <template #description>
          <p>{{ statusText || '暂无数据' }}</p>
          <p style="color: #999; font-size: 12px; margin-top: 8px;">状态: {{ graphStatus || '未知' }}</p>
        </template>
        <el-button @click="goBack">返回列表</el-button>
        <el-button @click="loadGraphData" type="primary">重新加载</el-button>
      </el-empty>
    </div>

    <!-- 节点详情抽屉 -->
    <el-drawer
      v-model="drawerVisible"
      title="节点详情"
      size="400px"
      :destroy-on-close="true"
    >
      <div v-if="selectedNode" class="node-detail">
        <div class="detail-header">
          <div class="node-icon" :style="{ backgroundColor: selectedNode.color }">
            <el-icon><Connection /></el-icon>
          </div>
          <div class="node-title">
            <h3>{{ selectedNode.name }}</h3>
            <el-tag :type="selectedNode.tagType" size="small">{{ selectedNode.type }}</el-tag>
          </div>
        </div>
        
        <div class="detail-section">
          <h4>基本信息</h4>
          <div class="info-item">
            <span class="label">节点ID:</span>
            <span class="value">{{ selectedNode.id }}</span>
          </div>
          <div class="info-item">
            <span class="label">连接数:</span>
            <span class="value">{{ selectedNode.degree }}</span>
          </div>
          <div class="info-item">
            <span class="label">节点类型:</span>
            <span class="value">{{ selectedNode.category }}</span>
          </div>
        </div>

        <div class="detail-section description-section" v-if="selectedNode.description">
          <h4>节点描述</h4>
          <div class="description-content" :class="{ 'collapsed': !descriptionExpanded }">
            {{ selectedNode.description }}
          </div>
          <div class="description-toggle" v-if="selectedNode.description.length > 200">
            <el-link type="primary" @click="descriptionExpanded = !descriptionExpanded">
              {{ descriptionExpanded ? '收起' : '展开' }}
            </el-link>
          </div>
        </div>

        <div class="detail-section" v-if="selectedNode.properties && Object.keys(selectedNode.properties).length > 0">
          <h4>属性信息</h4>
          <div v-for="(value, key) in selectedNode.properties" :key="key" class="info-item">
            <span class="label">{{ key }}:</span>
            <span class="value">{{ value }}</span>
          </div>
        </div>

        <!-- 关联节点部分暂时隐藏
        <div class="detail-section">
          <h4>关联节点</h4>
          <div>debug: {{ relatedNodesList }}</div>
          <div v-if="relatedNodesList && relatedNodesList.length > 0" class="related-nodes">
            <div 
              v-for="(node, index) in relatedNodesList" 
              :key="index" 
              class="related-node-item"
              @click="onRelatedNodeClick(relatedNodesList[index])"
            >
              <span class="node-dot" :style="{ backgroundColor: relatedNodesList[index].color }"></span>
              <span class="node-name">{{ relatedNodesList[index].name || '未命名' }}</span>
              <el-tag size="small" type="info">{{ relatedNodesList[index].relation }}</el-tag>
            </div>
          </div>
          <el-empty v-else description="暂无关联节点" :image-size="60" />
        </div>
        -->
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, shallowRef, computed, onMounted, onUnmounted, nextTick, toRaw } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'
import * as echarts from 'echarts'
import { ArrowLeft, Refresh, ZoomOut, ChatDotRound, Connection, Search, FullScreen } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const graphId = ref(route.params.id)

// 图谱数据
const graphName = ref('知识图谱')
const graphStatus = ref('')
const statusText = ref('')
const loading = ref(true)
const error = ref(false)

// ECharts 实例
let chartInstance = null
const graphContainer = ref(null)

// 抽屉和节点详情
const drawerVisible = ref(false)
const selectedNode = shallowRef(null)
const relatedNodesList = ref([])
const graphDataCache = ref({ nodes: [], edges: [] })
const descriptionExpanded = ref(false)

// 搜索相关
const searchKeyword = ref('')
const searchResults = ref([])
const currentSearchIndex = ref(-1)
const processedNodesCache = ref([])
const showSearchResults = ref(false)

// 全屏相关
const isFullscreen = ref(false)
const pageContainerRef = ref(null)

// 加载图谱数据
const loadGraphData = async () => {
  loading.value = true
  error.value = false
  
  try {
    // 获取图谱基本信息
    const graphResponse = await axios.get(`/api/requirement-analysis/knowledge-graphs/${graphId.value}/`)
    const graph = graphResponse.data
    graphName.value = graph.name
    graphStatus.value = graph.status
    
    if (graph.status !== 'completed') {
      statusText.value = graph.status === 'building' ? '知识图谱正在构建' :
                        graph.status === 'failed' ? '知识图谱构建失败' : '知识图谱未构建'
      loading.value = false
      return
    }
    
    // 获取可视化数据
    const vizResponse = await axios.get(`/api/requirement-analysis/knowledge-graphs/${graphId.value}/graph_data/`)
    const vizData = vizResponse.data
    
    if (vizData.success) {
      // 先结束加载状态，让 DOM 更新
      loading.value = false
      // 等待 DOM 完全渲染
      await nextTick()
      // 再等待一帧确保容器已创建
      await new Promise(resolve => requestAnimationFrame(resolve))
      renderGraph({
        nodes: vizData.nodes || [],
        edges: vizData.edges || []
      })
    } else {
      error.value = true
      ElMessage.error(vizData.error || '获取图谱数据失败')
    }
  } catch (err) {
    console.error('加载图谱数据失败:', err)
    error.value = true
    ElMessage.error('加载图谱数据失败')
  } finally {
    if (loading.value) {
      loading.value = false
    }
  }
}

// 渲染图谱
const renderGraph = (data) => {
  console.log('渲染图谱数据:', data)
  
  if (!graphContainer.value) {
    console.error('图谱容器不存在')
    return
  }
  
  if (!data.nodes || data.nodes.length === 0) {
    console.warn('没有节点数据')
    ElMessage.warning('暂无图谱数据')
    return
  }
  
  // 销毁旧实例
  if (chartInstance) {
    chartInstance.dispose()
  }
  
  // 创建新实例
  chartInstance = echarts.init(graphContainer.value)
  console.log('ECharts 实例创建成功')
  
  // 为节点计算连接数并分配颜色
  const nodeDegrees = {}
  const edgeColors = ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de', '#3ba272', '#fc8452', '#9a60b4']
  
  // 计算每个节点的连接数
  data.nodes.forEach(node => {
    nodeDegrees[node.id] = 0
  })
  data.edges.forEach(edge => {
    if (nodeDegrees[edge.source] !== undefined) nodeDegrees[edge.source]++
    if (nodeDegrees[edge.target] !== undefined) nodeDegrees[edge.target]++
  })
  
  // 根据连接数对节点分类
  const processedNodes = data.nodes.map((node, index) => {
    const degree = nodeDegrees[node.id] || 0
    let category = 0
    let color = '#5470c6'
    let size = 40
    
    if (degree >= 10) {
      category = 0  // 核心节点
      color = '#ee6666'  // 红色
      size = 70
    } else if (degree >= 5) {
      category = 1  // 重要节点
      color = '#fac858'  // 黄色
      size = 55
    } else if (degree >= 2) {
      category = 2  // 普通节点
      color = '#5470c6'  // 蓝色
      size = 45
    } else {
      category = 3  // 边缘节点
      color = '#91cc75'  // 绿色
      size = 35
    }
    
    // 获取节点名称（优先使用原始 label，如果 label 是对象则使用 name）
    let nodeName = node.name || ''
    if (node.label && typeof node.label === 'string') {
      nodeName = node.label
    }
    
    return {
      ...node,
      name: nodeName,
      category,
      dataIndex: index,
      itemStyle: {
        color: color,
        borderColor: '#fff',
        borderWidth: 2,
        shadowBlur: 10,
        shadowColor: color + '80'
      },
      symbolSize: size,
      label: {
        show: true,
        position: degree >= 5 ? 'inside' : 'bottom',
        color: degree >= 5 ? '#fff' : '#333',
        fontSize: degree >= 5 ? 14 : 12,
        fontWeight: degree >= 5 ? 'bold' : 'normal',
        textBorderColor: degree >= 5 ? 'transparent' : '#fff',
        textBorderWidth: degree >= 5 ? 0 : 2,
        textShadowColor: degree >= 5 ? 'rgba(0,0,0,0.3)' : 'rgba(255,255,255,0.8)',
        textShadowBlur: degree >= 5 ? 2 : 3,
        textShadowOffsetX: 0,
        textShadowOffsetY: 1
      }
    }
  })
  
  // 为边分配不同颜色和样式
  const processedEdges = data.edges.map((edge, index) => {
    const colorIndex = index % edgeColors.length
    const width = Math.max(1, Math.min(5, (edge.weight || 1) / 2))
    
    return {
      ...edge,
      lineStyle: {
        color: edgeColors[colorIndex],
        width: width,
        curveness: 0.2,
        opacity: 0.7
      }
    }
  })
  
  const option = {
    tooltip: {
      trigger: 'item',
      formatter: (params) => {
        if (params.dataType === 'node') {
          // 直接使用 name 字段（已在上面的处理中设置为字符串）
          const name = params.data.name || ''
          const degree = nodeDegrees[params.data.id] || 0
          let type = '边缘节点'
          if (degree >= 10) type = '核心节点'
          else if (degree >= 5) type = '重要节点'
          else if (degree >= 2) type = '普通节点'
          return `<strong>${name}</strong><br/>类型: ${type}<br/>连接数: ${degree}`
        } else if (params.dataType === 'edge') {
          return `关系连接<br/>权重: ${params.data.weight || 1}`
        }
        return params.name
      }
    },
    legend: {
      data: ['核心节点', '重要节点', '普通节点', '边缘节点'],
      top: 10,
      left: 10,
      itemGap: 20,
      backgroundColor: 'rgba(255,255,255,0.9)',
      borderRadius: 4,
      padding: 10
    },
    series: [
      {
        type: 'graph',
        layout: 'force',
        data: processedNodes,
        links: processedEdges,
        categories: [
          { name: '核心节点', itemStyle: { color: '#ee6666' } },
          { name: '重要节点', itemStyle: { color: '#fac858' } },
          { name: '普通节点', itemStyle: { color: '#5470c6' } },
          { name: '边缘节点', itemStyle: { color: '#91cc75' } }
        ],
        roam: true,
        draggable: true,
        focusNodeAdjacency: true,
        force: {
          repulsion: 500,
          edgeLength: [100, 200],
          gravity: 0.1,
          layoutAnimation: true
        },
        selectedMode: 'single',
        select: {
          itemStyle: {
            shadowBlur: 30,
            shadowColor: 'rgba(0,0,0,0.5)',
            borderColor: '#fff',
            borderWidth: 4
          },
          label: {
            show: true,
            fontSize: 16,
            fontWeight: 'bold'
          }
        },
        emphasis: {
          focus: 'adjacency',
          scale: 1.2,
          label: {
            show: true,
            fontSize: 14,
            fontWeight: 'bold'
          }
        },
        lineStyle: {
          curveness: 0.2
        }
      }
    ]
  }
  
  chartInstance.setOption(option)

  // 缓存原始图谱数据用于点击查询
  graphDataCache.value = { nodes: data.nodes, edges: data.edges }
  // 缓存处理后的节点用于搜索
  processedNodesCache.value = processedNodes

  // 绑定节点点击事件
  chartInstance.on('click', (params) => {
    if (params.dataType === 'node') {
      handleNodeClick(params.data)
    }
  })
  
  // 响应式调整
  window.addEventListener('resize', handleResize)
}

// 处理窗口大小变化
const handleResize = () => {
  if (chartInstance) {
    chartInstance.resize()
  }
}

// 刷新可视化
const refreshVisualization = () => {
  loadGraphData()
}

// 重置缩放
const resetZoom = () => {
  if (chartInstance) {
    chartInstance.dispatchAction({
      type: 'restore'
    })
  }
}

// 返回列表
const goBack = () => {
  router.push('/ai-assistant/knowledge-graph/overview')
}

// 处理节点点击
const handleNodeClick = (nodeData) => {
  console.log('点击节点数据:', nodeData)
  console.log('缓存节点数据:', graphDataCache.value.nodes.find(n => n.id === nodeData.id))

  // 从缓存的边中计算连接数 - 需要处理source/target可能是节点名称的情况
  const degree = graphDataCache.value.edges.filter(e => {
    const sourceMatch = e.source === nodeData.id || e.source === nodeData.name
    const targetMatch = e.target === nodeData.id || e.target === nodeData.name
    return sourceMatch || targetMatch
  }).length

  let type = '边缘节点'
  let tagType = 'success'
  let category = '普通节点'
  let color = '#91cc75'

  if (degree >= 10) {
    type = '核心节点'
    tagType = 'danger'
    category = '核心节点'
    color = '#ee6666'
  } else if (degree >= 5) {
    type = '重要节点'
    tagType = 'warning'
    category = '重要节点'
    color = '#fac858'
  } else if (degree >= 2) {
    type = '普通节点'
    tagType = 'primary'
    category = '普通节点'
    color = '#5470c6'
  }

  // 获取关联节点
  const relatedNodes = []
  console.log('构建关联节点，当前节点:', nodeData.id, nodeData.name, nodeData.label)
  console.log('所有边数据:', graphDataCache.value.edges)
  console.log('节点数据示例:', graphDataCache.value.nodes.slice(0, 3))
  graphDataCache.value.edges.forEach((edge, index) => {
    const sourceMatch = String(edge.source) === String(nodeData.id) || edge.source === nodeData.name || edge.source === nodeData.label
    const targetMatch = String(edge.target) === String(nodeData.id) || edge.target === nodeData.name || edge.target === nodeData.label
    
    console.log(`边[${index}]: source=${edge.source}, target=${edge.target}, label=${edge.label}, sourceMatch=${sourceMatch}, targetMatch=${targetMatch}`)

    if (sourceMatch) {
      // 找到target节点 - 可能通过ID或名称匹配
      const targetNode = graphDataCache.value.nodes.find(n =>
        n.id === edge.target || n.name === edge.target || n.label === edge.target
      )
      console.log('sourceMatch, edge.target:', edge.target, '找到targetNode:', targetNode)
      console.log('targetNode 详情:', { id: targetNode?.id, label: targetNode?.label, name: targetNode?.name, description: targetNode?.description?.slice(0, 50) })
      if (targetNode) {
        // 计算目标节点的连接数来确定颜色
        const targetDegree = graphDataCache.value.edges.filter(e =>
          e.source === targetNode.id || e.target === targetNode.id ||
          e.source === targetNode.name || e.target === targetNode.name ||
          e.source === targetNode.label || e.target === targetNode.label
        ).length
        let targetColor = '#91cc75'
        if (targetDegree >= 10) targetColor = '#ee6666'
        else if (targetDegree >= 5) targetColor = '#fac858'
        else if (targetDegree >= 2) targetColor = '#5470c6'

        // 获取节点名称（优先使用label，然后是name）
        const targetName = (targetNode.label && typeof targetNode.label === 'string') ? targetNode.label : 
                          (targetNode.name && typeof targetNode.name === 'string') ? targetNode.name : '未命名'
        const targetNodeData = JSON.parse(JSON.stringify({
          id: targetNode.id,
          name: targetName,
          color: targetColor,
          relation: edge.label || '关联'
        }))
        relatedNodes.push(targetNodeData)
      }
    }
    
    if (targetMatch) {
      // 找到source节点 - 可能通过ID或名称匹配
      const sourceNode = graphDataCache.value.nodes.find(n =>
        n.id === edge.source || n.name === edge.source || n.label === edge.source
      )
      console.log('targetMatch, edge.source:', edge.source, '找到sourceNode:', sourceNode)
      console.log('sourceNode 详情:', { id: sourceNode?.id, label: sourceNode?.label, name: sourceNode?.name, description: sourceNode?.description?.slice(0, 50) })
      if (sourceNode) {
        // 计算源节点的连接数来确定颜色
        const sourceDegree = graphDataCache.value.edges.filter(e =>
          e.source === sourceNode.id || e.target === sourceNode.id ||
          e.source === sourceNode.name || e.target === sourceNode.name ||
          e.source === sourceNode.label || e.target === sourceNode.label
        ).length
        let sourceColor = '#91cc75'
        if (sourceDegree >= 10) sourceColor = '#ee6666'
        else if (sourceDegree >= 5) sourceColor = '#fac858'
        else if (sourceDegree >= 2) sourceColor = '#5470c6'

        // 获取节点名称（优先使用label，然后是name）
        const sourceName = (sourceNode.label && typeof sourceNode.label === 'string') ? sourceNode.label : 
                          (sourceNode.name && typeof sourceNode.name === 'string') ? sourceNode.name : '未命名'
        const sourceNodeData = JSON.parse(JSON.stringify({
          id: sourceNode.id,
          name: sourceName,
          color: sourceColor,
          relation: edge.label || '关联'
        }))
        relatedNodes.push(sourceNodeData)
      }
    }
  })

  // 从原始数据中获取节点名称和描述（优先使用label，然后是name）
  const originalNode = graphDataCache.value.nodes.find(n => n.id === nodeData.id)
  const nodeName = originalNode ? (originalNode.label || originalNode.name || '未命名') : (nodeData.name || '未命名')
  // 优先从原始节点获取描述，如果没有则从点击的节点数据获取
  const nodeDescription = originalNode?.description || nodeData.description || ''
  console.log('节点描述:', nodeDescription)
  console.log('关联节点列表:', relatedNodes.map(n => ({ id: n.id, name: n.name, relation: n.relation })))

  selectedNode.value = {
    id: nodeData.id,
    name: nodeName,
    type,
    tagType,
    category,
    color,
    degree,
    description: nodeDescription,
    properties: nodeData.properties || {}
  }
  
  relatedNodesList.value = relatedNodes

  drawerVisible.value = true
}

// 获取节点名称
const getNodeName = (node, index) => {
  if (!node) return '未命名'
  console.log('getNodeName:', { node, index, relatedNodesList: relatedNodesList.value })
  
  // 直接从 relatedNodesList 中获取数据
  const listNode = relatedNodesList.value[index]
  if (listNode && listNode.name) {
    return listNode.name
  }
  
  // 从原始 graphDataCache 中查找节点
  const graphNode = graphDataCache.value.nodes.find(n => String(n.id) === String(node.id))
  if (graphNode) {
    return graphNode.label || graphNode.name || '未命名'
  }
  
  return '未命名'
}

// 处理关联节点点击
const onRelatedNodeClick = (node) => {
  const nodeData = graphDataCache.value.nodes.find(n => String(n.id) === String(node.id))
  if (nodeData) {
    handleNodeClick(nodeData)
  }
}

// 搜索处理
const handleSearch = () => {
  const keyword = searchKeyword.value.trim().toLowerCase()
  if (!keyword) {
    searchResults.value = []
    currentSearchIndex.value = -1
    return
  }

  const matchedNodes = processedNodesCache.value.filter(node => {
    const nodeName = (node.name || '').toLowerCase()
    return nodeName.includes(keyword)
  })

  // 根据节点ID去重
  const uniqueNodes = []
  const seenIds = new Set()
  for (const node of matchedNodes) {
    if (!seenIds.has(node.id)) {
      seenIds.add(node.id)
      uniqueNodes.push(node)
    }
  }

  searchResults.value = uniqueNodes
  showSearchResults.value = true
  currentSearchIndex.value = -1
}

// 关闭搜索结果
const closeSearchResults = () => {
  showSearchResults.value = false
}

// 清空搜索
const clearSearch = () => {
  searchKeyword.value = ''
  searchResults.value = []
  showSearchResults.value = false
  currentSearchIndex.value = -1
  // 取消高亮和选中状态
  if (chartInstance) {
    chartInstance.dispatchAction({
      type: 'downplay',
      seriesIndex: 0
    })
    chartInstance.dispatchAction({
      type: 'unselect',
      seriesIndex: 0
    })
  }
}

// 定位节点
const locateNode = (node, index) => {
  currentSearchIndex.value = index

  // 将选中的节点名称回显到输入框
  searchKeyword.value = node.name || ''

  // 关闭搜索结果下拉菜单
  showSearchResults.value = false

  if (!chartInstance) return

  // 取消之前的选中状态和高亮
  chartInstance.dispatchAction({
    type: 'unselect',
    seriesIndex: 0
  })
  chartInstance.dispatchAction({
    type: 'downplay',
    seriesIndex: 0
  })
  // 高亮选中节点 - 使用 highlight 配合 focus 实现蒙尘效果
  chartInstance.dispatchAction({
    type: 'highlight',
    seriesIndex: 0,
    name: node.name
  })

  // 聚焦到节点位置
  const focusNode = () => {
    // 获取图表的当前状态
    const option = chartInstance.getOption()
    const series = option.series[0]

    if (!series || !series.data) return

    // 找到目标节点
    const targetNode = series.data.find(n => n.id === node.id)
    if (!targetNode) return

    // 如果坐标还没计算好，稍后重试
    if (targetNode.x == null || targetNode.y == null) {
      setTimeout(focusNode, 200)
      return
    }

    // 获取容器尺寸
    const width = graphContainer.value.clientWidth
    const height = graphContainer.value.clientHeight

    // 计算新的中心点，使节点位于画布中心
    // ECharts center 是相对于容器左上角的偏移量
    const centerX = width / 2 - targetNode.x
    const centerY = height / 2 - targetNode.y

    // 设置新的视图状态
    chartInstance.setOption({
      series: [{
        center: [centerX, centerY],
        zoom: 1.5
      }]
    })

    // 显示 tooltip
    chartInstance.dispatchAction({
      type: 'showTip',
      seriesIndex: 0,
      dataIndex: node.dataIndex
    })
  }

  // 延迟执行，等待布局稳定
  setTimeout(focusNode, 300)
}

// 组件挂载时加载数据
onMounted(() => {
  loadGraphData()
})

// 全屏切换
const toggleFullscreen = async () => {
  const element = pageContainerRef.value
  if (!element) return

  try {
    if (!isFullscreen.value) {
      // 进入全屏
      if (element.requestFullscreen) {
        await element.requestFullscreen()
      } else if (element.webkitRequestFullscreen) {
        await element.webkitRequestFullscreen()
      } else if (element.msRequestFullscreen) {
        await element.msRequestFullscreen()
      }
    } else {
      // 退出全屏
      if (document.exitFullscreen) {
        await document.exitFullscreen()
      } else if (document.webkitExitFullscreen) {
        await document.webkitExitFullscreen()
      } else if (document.msExitFullscreen) {
        await document.msExitFullscreen()
      }
    }
  } catch (err) {
    console.error('全屏切换失败:', err)
    ElMessage.error('全屏切换失败')
  }
}

// 监听全屏状态变化
const handleFullscreenChange = () => {
  isFullscreen.value = !!(
    document.fullscreenElement ||
    document.webkitFullscreenElement ||
    document.msFullscreenElement
  )
  // 全屏状态变化后，调整图表大小
  setTimeout(() => {
    if (chartInstance) {
      chartInstance.resize()
    }
  }, 100)
}

// 组件挂载时加载数据
onMounted(() => {
  loadGraphData()
  // 监听全屏状态变化
  document.addEventListener('fullscreenchange', handleFullscreenChange)
  document.addEventListener('webkitfullscreenchange', handleFullscreenChange)
  document.addEventListener('msfullscreenchange', handleFullscreenChange)
})

// 组件卸载时清理
onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  // 移除全屏监听
  document.removeEventListener('fullscreenchange', handleFullscreenChange)
  document.removeEventListener('webkitfullscreenchange', handleFullscreenChange)
  document.removeEventListener('msfullscreenchange', handleFullscreenChange)
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
})
</script>

<style scoped>
.page-container {
  padding: 20px;
  background: #f5f7fa;
  min-height: 100vh;
}

/* 全屏模式样式 */
.page-container.is-fullscreen {
  padding: 0;
  background: #fff;
  display: flex;
  flex-direction: column;
  height: 100vh;
}

.page-container.is-fullscreen .filter-bar {
  margin-bottom: 0;
  border-radius: 0;
  box-shadow: none;
  border-bottom: 1px solid #e4e7ed;
}

.page-container.is-fullscreen .graph-container {
  flex: 1;
  border-radius: 0;
  box-shadow: none;
  margin: 0;
  height: auto;
  min-height: auto;
}

.filter-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding: 16px 20px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.graph-name {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.filter-bar-spacer {
  flex: 1;
}

/* 搜索框样式 */
.search-box {
  position: relative;
  margin-right: 16px;
  width: 280px;
}

.search-box .el-input {
  --el-input-border-radius: 8px;
}

.search-box .el-input__wrapper {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  border: 1px solid rgba(123, 66, 246, 0.15);
  transition: all 0.3s ease;
}

.search-box .el-input__wrapper:hover,
.search-box .el-input__wrapper.is-focus {
  box-shadow: 0 4px 12px rgba(123, 66, 246, 0.12);
  border-color: rgba(123, 66, 246, 0.3);
}

.search-results {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  margin-top: 8px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  max-height: 320px;
  overflow-y: auto;
  z-index: 100;
  border: 1px solid rgba(123, 66, 246, 0.1);
}

.search-results-header {
  padding: 10px 16px;
  font-size: 12px;
  color: #909399;
  border-bottom: 1px solid #f0f0f0;
  background: #fafafa;
}

.search-result-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  cursor: pointer;
  transition: all 0.2s ease;
  border-bottom: 1px solid #f5f5f5;
}

.search-result-item:last-child {
  border-bottom: none;
}

.search-result-item:hover {
  background: #f5f3ff;
}

.search-result-item.active {
  background: #ede9fe;
}

.search-result-item .node-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.search-result-item .node-name {
  flex: 1;
  font-size: 14px;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.header-actions .el-button {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  font-weight: 500;
  padding: 8px 16px;
  border-radius: 6px;
  transition: all 0.3s ease;
  border: none;
}

.header-actions .el-button .el-icon {
  font-size: 14px;
}

/* 默认按钮样式（刷新、重置缩放） */
.header-actions .el-button:not(.el-button--primary) {
  background: #f5f3ff;
  color: #7b42f6;
  border: 1px solid rgba(123, 66, 246, 0.2);
}

.header-actions .el-button:not(.el-button--primary):hover {
  background: #ede9fe;
  border-color: rgba(123, 66, 246, 0.4);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(123, 66, 246, 0.15);
}

/* 主要按钮样式（智能问答） */
.header-actions .el-button.el-button--primary {
  background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
  border: none;
  color: #ffffff;
  font-weight: 600;
}

.header-actions .el-button.el-button--primary:hover {
  background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(123, 66, 246, 0.4);
}

.loading-container,
.error-container,
.empty-container {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
  height: calc(100vh - 140px);
}

.card-container {
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
  padding: 20px;
  height: calc(100vh - 140px);
}

.graph-canvas {
  width: 100%;
  height: 100%;
  border-radius: 4px;
}

/* 节点详情抽屉样式 */
.node-detail {
  padding: 0 4px;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.detail-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding-bottom: 20px;
  border-bottom: 1px solid #e4e7ed;
  margin-bottom: 20px;
}

.node-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 24px;
  flex-shrink: 0;
}

.node-title h3 {
  margin: 0 0 8px 0;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.detail-section {
  margin-bottom: 24px;
}

.detail-section h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  font-weight: 600;
  color: #606266;
  padding-left: 8px;
  border-left: 3px solid #7b42f6;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  background: #f5f7fa;
  border-radius: 6px;
  margin-bottom: 8px;
}

.info-item .label {
  font-size: 13px;
  color: #909399;
}

.info-item .value {
  font-size: 13px;
  color: #303133;
  font-weight: 500;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.description-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.description-section .description-content {
  flex: 1;
  min-height: 0;
  max-height: none;
}

.description-content {
  padding: 12px 0;
  font-size: 14px;
  line-height: 1.8;
  color: #303133;
  white-space: pre-wrap;
  word-break: break-word;
}

.related-nodes {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.related-node-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.related-node-item:hover {
  background: #ede9fe;
  transform: translateX(4px);
}

.node-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.node-name {
  flex: 1;
  font-size: 14px;
  color: #303133;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
