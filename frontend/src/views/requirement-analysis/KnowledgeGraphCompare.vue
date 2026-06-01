<template>
  <div class="page-container">
    <!-- 版本选择区 -->
    <div class="card-container version-selector-compact">
      <div class="version-compare-row">
        <!-- 基准版本 -->
        <div class="version-box-compact">
          <div class="version-label">
            <el-icon><Document /></el-icon>
            <span>基准版本</span>
          </div>
          <div class="select-group">
            <el-select v-model="baseGraphId" placeholder="选择图谱" size="default" @change="onBaseGraphChange">
              <el-option
                v-for="g in allGraphs"
                :key="g.id"
                :label="g.name"
                :value="g.id"
              />
            </el-select>
            <el-select v-model="baseVersion" placeholder="选择版本" size="default" value-key="id" :disabled="!baseGraphId">
              <el-option
                v-for="v in baseGraphVersions"
                :key="v.id"
                :label="formatVersionLabel(v)"
                :value="v"
              >
                <div class="version-option">
                  <span class="version-number">{{ v.version_number }}</span>
                  <span v-if="v.version_name" class="version-name">{{ v.version_name }}</span>
                </div>
              </el-option>
            </el-select>
          </div>
        </div>

        <!-- VS 标识 -->
        <div class="vs-divider">
          <span class="vs-text">VS</span>
        </div>

        <!-- 对比版本 -->
        <div class="version-box-compact">
          <div class="version-label">
            <el-icon><Document /></el-icon>
            <span>对比版本</span>
          </div>
          <div class="select-group">
            <el-select v-model="compareGraphId" placeholder="选择图谱" size="default" @change="onCompareGraphChange">
              <el-option
                v-for="g in allGraphs"
                :key="g.id"
                :label="g.name"
                :value="g.id"
              />
            </el-select>
            <el-select v-model="compareVersion" placeholder="选择版本" size="default" value-key="id" :disabled="!compareGraphId">
              <el-option
                v-for="v in compareGraphVersions"
                :key="v.id"
                :label="formatVersionLabel(v)"
                :value="v"
              >
                <div class="version-option">
                  <span class="version-number">{{ v.version_number }}</span>
                  <span v-if="v.version_name" class="version-name">{{ v.version_name }}</span>
                </div>
              </el-option>
            </el-select>
          </div>
        </div>

        <!-- 开始对比按钮 -->
        <div class="compare-action">
          <el-button
            type="primary"
            @click="startCompare"
            :loading="loading"
            :disabled="!baseVersion || !compareVersion || baseVersion.id === compareVersion.id"
            size="default"
          >
            <el-icon><ScaleToOriginal /></el-icon>
            <span>对比</span>
          </el-button>
        </div>
      </div>

      <el-alert
        v-if="baseVersion && compareVersion && baseVersion.id === compareVersion.id"
        title="基准版本和对比版本不能相同"
        type="warning"
        :closable="false"
        class="compact-alert"
      />
    </div>

    <!-- 对比结果 -->
    <div v-if="compareResult" class="compare-result">
      <!-- 统计概览 -->
      <div class="card-container">
        <el-row :gutter="20" class="stats-row">
          <el-col :span="8">
            <div class="stat-card added">
              <div class="stat-icon">
                <el-icon><CirclePlusFilled /></el-icon>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ stats.added }}</div>
                <div class="stat-label">新增需求</div>
              </div>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="stat-card modified">
              <div class="stat-icon">
                <el-icon><Edit /></el-icon>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ stats.modified }}</div>
                <div class="stat-label">修改需求</div>
              </div>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="stat-card removed">
              <div class="stat-icon">
                <el-icon><RemoveFilled /></el-icon>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ stats.removed }}</div>
                <div class="stat-label">删除需求</div>
              </div>
            </div>
          </el-col>
        </el-row>
      </div>

      <!-- 详细分析 -->
      <div class="card-container">
        <div class="section-header">
          <span class="section-title">对比分析结果</span>
          <div class="section-actions">
            <el-button text @click="exportResult">
              <el-icon><Download /></el-icon> 导出报告
            </el-button>
          </div>
        </div>
        <div class="analysis-content" v-html="formatAnalysis(compareResult.analysis)"></div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else-if="!loading" class="empty-state">
      <div class="empty-icon">
        <el-icon><ScaleToOriginal /></el-icon>
      </div>
      <div class="empty-title">选择两个版本后点击开始对比</div>
      <div class="empty-desc">选择基准版本和对比版本，系统将自动分析版本间的差异</div>
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="card-container loading-container">
      <el-skeleton :rows="10" animated />
      <p class="loading-text">AI 正在分析版本差异，请稍候...</p>
    </div>



    <!-- 创建版本对话框 -->
    <el-dialog
      v-model="showCreateVersionDialog"
      title="创建知识图谱版本"
      width="500px"
    >
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
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import {
  ArrowLeft, ScaleToOriginal, CirclePlusFilled, Edit,
  RemoveFilled, Download, Document, ArrowRight, Plus
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const graphId = route.query.graph_id

// 状态
const loading = ref(false)
const baseVersion = ref(null)
const compareVersion = ref(null)
const baseGraphId = ref(null)
const compareGraphId = ref(null)
const baseGraph = ref(null)
const compareGraph = ref(null)
const baseGraphVersions = ref([])
const compareGraphVersions = ref([])
const allGraphs = ref([])
const compareResult = ref(null)
const graphInfo = ref(null)
const showCreateVersionDialog = ref(false)

// 创建版本表单
const createVersionForm = ref({
  version_number: '',
  version_name: '',
  description: ''
})
const creatingVersion = ref(false)

// 统计
const stats = ref({
  added: 0,
  modified: 0,
  removed: 0
})

// 对比模板
const compareTemplates = [
  {
    name: '最新两个版本对比',
    description: '自动选择最新的两个版本进行对比'
  },
  {
    name: '最早 vs 最新',
    description: '对比第一个版本和最新版本的变化'
  }
]

// 格式化版本标签
const formatVersionLabel = (version) => {
  if (!version) return ''
  return `${version.version_number}${version.version_name ? ' - ' + version.version_name : ''}`
}

// 获取图谱信息
const fetchGraphInfo = async () => {
  if (!graphId) return

  try {
    const response = await api.get(`/requirement-analysis/knowledge-graphs/${graphId}/`)
    graphInfo.value = response.data

    if (graphInfo.value.status !== 'completed') {
      ElMessage.warning('知识图谱尚未构建完成，请先完成构建')
      router.push({ name: 'KnowledgeGraphOverview' })
      return
    }

    // 获取所有图谱列表
    await fetchAllGraphs()
  } catch (error) {
    console.error('获取图谱信息失败:', error)
    ElMessage.error('获取图谱信息失败')
  }
}

// 获取所有图谱列表
const fetchAllGraphs = async () => {
  try {
    const response = await axios.get('/requirement-analysis/knowledge-graphs/')
    allGraphs.value = response.data.results || response.data

    // 设置默认选中的图谱
    if (graphId) {
      const graphIdNum = typeof graphId === 'string' ? parseInt(graphId) : graphId
      const currentGraph = allGraphs.value.find(g => g.id === graphIdNum)
      if (currentGraph) {
        baseGraphId.value = currentGraph.id
        compareGraphId.value = currentGraph.id
        baseGraph.value = currentGraph
        compareGraph.value = currentGraph
        await fetchBaseGraphVersions()
        await fetchCompareGraphVersions()
      }
    }
  } catch (error) {
    console.error('获取图谱列表失败:', error)
    ElMessage.error('获取图谱列表失败')
  }
}

// 获取基准图谱的版本列表
const fetchBaseGraphVersions = async () => {
  if (!baseGraphId.value) return
  try {
    const response = await api.get(`/requirement-analysis/knowledge-graphs/${baseGraphId.value}/versions/`)
    baseGraphVersions.value = response.data
  } catch (error) {
    console.error('获取基准版本列表失败:', error)
    baseGraphVersions.value = []
  }
}

// 获取对比图谱的版本列表
const fetchCompareGraphVersions = async () => {
  if (!compareGraphId.value) return
  try {
    const response = await api.get(`/requirement-analysis/knowledge-graphs/${compareGraphId.value}/versions/`)
    compareGraphVersions.value = response.data
  } catch (error) {
    console.error('获取对比版本列表失败:', error)
    compareGraphVersions.value = []
  }
}

// 基准图谱变更
const onBaseGraphChange = async (id) => {
  baseGraphId.value = id
  baseVersion.value = null
  baseGraph.value = allGraphs.value.find(g => g.id === id) || null
  await fetchBaseGraphVersions()
}

// 对比图谱变更
const onCompareGraphChange = async (id) => {
  compareGraphId.value = id
  compareVersion.value = null
  compareGraph.value = allGraphs.value.find(g => g.id === id) || null
  await fetchCompareGraphVersions()
}

// 创建版本
const createVersion = async () => {
  if (!createVersionForm.value.version_number) {
    ElMessage.warning('请输入版本号')
    return
  }

  creatingVersion.value = true
  try {
    const response = await api.post(`/requirement-analysis/knowledge-graphs/${graphId}/create_version/`, {
      version_number: createVersionForm.value.version_number,
      version_name: createVersionForm.value.version_name,
      description: createVersionForm.value.description
    })

    if (response.data.success) {
      ElMessage.success('版本创建成功')
      showCreateVersionDialog.value = false
      createVersionForm.value = { version_number: '', version_name: '', description: '' }
      // 刷新当前图谱的版本列表
      await fetchBaseGraphVersions()
      await fetchCompareGraphVersions()
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

// 开始对比
const startCompare = async () => {
  if (!baseVersion.value || !compareVersion.value) {
    ElMessage.warning('请选择两个版本')
    return
  }

  if (baseVersion.value.id === compareVersion.value.id) {
    ElMessage.warning('基准版本和对比版本不能相同')
    return
  }

  // 检查两个版本是否来自同一个图谱
  if (baseGraphId.value !== compareGraphId.value) {
    ElMessage.warning('基准版本和对比版本必须来自同一个知识图谱')
    return
  }

  loading.value = true
  compareResult.value = null

  try {
    // 使用真正的版本对比 API
    const response = await api.post(`/requirement-analysis/knowledge-graphs/${graphId}/compare_versions_real/`, {
      base_version_id: baseVersion.value.id,
      compare_version_id: compareVersion.value.id
    })

    // 检查后端返回的成功状态
    if (!response.data.success) {
      ElMessage.error(response.data.error || '版本对比失败')
      compareResult.value = null
      return
    }

    compareResult.value = response.data

    // 使用后端返回的真实统计数据
    if (response.data.stats) {
      stats.value = {
        added: response.data.stats.entities.added + response.data.stats.relations.added,
        modified: 0, // 实体和关系的修改需要更复杂的对比逻辑
        removed: response.data.stats.entities.removed + response.data.stats.relations.removed
      }
    }

  } catch (error) {
    console.error('对比失败:', error)
    ElMessage.error('版本对比失败')
  } finally {
    loading.value = false
  }
}

// 解析统计信息
const parseStats = (analysis) => {
  // 尝试从分析文本中提取统计数字
  const addedMatch = analysis.match(/新增[:：]\s*(\d+)/i) || analysis.match(/(\d+)\s*个.*新增/i)
  const modifiedMatch = analysis.match(/修改[:：]\s*(\d+)/i) || analysis.match(/(\d+)\s*个.*修改/i)
  const removedMatch = analysis.match(/删除[:：]\s*(\d+)/i) || analysis.match(/(\d+)\s*个.*删除/i)

  stats.value = {
    added: addedMatch ? parseInt(addedMatch[1]) : 0,
    modified: modifiedMatch ? parseInt(modifiedMatch[1]) : 0,
    removed: removedMatch ? parseInt(removedMatch[1]) : 0
  }
}

// 应用模板
const applyTemplate = (template) => {
  if (template.name === '最新两个版本对比') {
    // 需要同一个图谱有至少两个版本
    if (baseGraphVersions.value.length >= 2) {
      baseVersion.value = baseGraphVersions.value[1]  // 第二新
      compareVersion.value = baseGraphVersions.value[0]  // 最新
      // 确保对比图谱和基准图谱相同
      compareGraphId.value = baseGraphId.value
      compareGraph.value = baseGraph.value
      compareGraphVersions.value = [...baseGraphVersions.value]
    } else {
      ElMessage.warning('当前图谱至少需要两个版本才能进行对比')
    }
  } else if (template.name === '最早 vs 最新') {
    if (baseGraphVersions.value.length >= 2) {
      baseVersion.value = baseGraphVersions.value[baseGraphVersions.value.length - 1]  // 最早
      compareVersion.value = baseGraphVersions.value[0]  // 最新
      compareGraphId.value = baseGraphId.value
      compareGraph.value = baseGraph.value
      compareGraphVersions.value = [...baseGraphVersions.value]
    } else {
      ElMessage.warning('当前图谱至少需要两个版本才能进行对比')
    }
  }
}

// 格式化分析结果
const formatAnalysis = (analysis) => {
  if (!analysis) return ''

  // 简单的 Markdown 格式化
  return analysis
    .replace(/#{1,6}\s+(.+)/g, '<h4>$1</h4>')
    .replace(/\*\*(.+?)\*\*/g, '<strong style="color: #409eff;">$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`(.+?)`/g, '<code style="background: #f4f4f5; padding: 2px 6px; border-radius: 4px;">$1</code>')
    .replace(/^-\s+(.+)$/gm, '<li style="margin: 8px 0;">$1</li>')
    .replace(/\n\n/g, '</p><p>')
    .replace(/^(.+)$/gm, (match) => {
      if (match.startsWith('<')) return match
      return `<p>${match}</p>`
    })
}

// 导出结果
const exportResult = () => {
  if (!compareResult.value) return

  const content = `# 需求版本对比报告

## 对比版本
- 基准版本: ${baseVersion.value}
- 对比版本: ${compareVersion.value}

## 统计概览
- 新增需求: ${stats.value.added} 个
- 修改需求: ${stats.value.modified} 个
- 删除需求: ${stats.value.removed} 个

## 详细分析
${compareResult.value.analysis}

---
生成时间: ${new Date().toLocaleString('zh-CN')}
`

  const blob = new Blob([content], { type: 'text/markdown' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `版本对比_${baseVersion.value}_${compareVersion.value}_${Date.now()}.md`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)

  ElMessage.success('报告已导出')
}

// 返回
const goBack = () => {
  router.push({ name: 'KnowledgeGraphOverview' })
}

onMounted(() => {
  if (!graphId) {
    ElMessage.error('未指定知识图谱')
    router.push({ name: 'KnowledgeGraphOverview' })
    return
  }

  fetchGraphInfo()
})
</script>

<style scoped>
/* 页面容器 */
.page-container {
  padding: 20px;
  background: #f5f7fa;
  min-height: calc(100vh - 60px);
  --el-color-primary: #7b42f6;
  --el-color-primary-light-3: #9370db;
  --el-color-primary-light-5: #a888e0;
  --el-color-primary-light-7: #c2a9f3;
  --el-color-primary-light-9: #f8f7ff;
  display: flex;
  flex-direction: column;
}

.page-container > .card-container:last-child {
  flex: 1;
}

/* 筛选栏 */
.filter-bar {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
  background: #fff;
  padding: 16px 20px;
  border-radius: 8px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.filter-bar-spacer {
  flex: 1;
}

.graph-name {
  font-size: 14px;
  color: #606266;
  font-weight: 500;
}

/* 卡片容器 */
.card-container {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

/* 紧凑版本选择器 */
.version-selector-compact {
  padding: 16px 20px;
}

.version-compare-row {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.version-box-compact {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1;
  min-width: 280px;
}

.version-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 500;
  color: #606266;
}

.version-label .el-icon {
  font-size: 14px;
  color: #909399;
}

.select-group {
  display: flex;
  gap: 8px;
}

.select-group .el-select {
  flex: 1;
}

.vs-divider {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 8px;
  margin-top: 21px;
}

.vs-text {
  font-size: 14px;
  font-weight: 600;
  color: #c0c4cc;
  background: #f5f7fa;
  padding: 4px 10px;
  border-radius: 12px;
}

.compare-action {
  display: flex;
  align-items: center;
  margin-top: 21px;
}

.compare-action .el-button {
  height: 32px;
}

.compact-alert {
  margin-top: 12px;
  padding: 8px 12px;
}

.compact-alert :deep(.el-alert__content) {
  padding: 0;
}

/* 版本选择区 */
.selector-row {
  display: flex;
  align-items: flex-end;
  gap: 24px;
  flex-wrap: wrap;
}

.version-box {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.version-box label {
  font-size: 14px;
  color: #606266;
  font-weight: 500;
}

.vs-label {
  font-size: 20px;
  font-weight: bold;
  color: #909399;
  padding-bottom: 8px;
}

/* 区块标题 */
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #e4e7ed;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.section-actions {
  display: flex;
  gap: 8px;
}

/* 统计卡片 */
.stats-row {
  margin: 0 !important;
}

.stat-card {
  display: flex;
  align-items: center;
  padding: 20px;
  border-radius: 8px;
  background: #f5f7fa;
  transition: all 0.3s;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.stat-card.added {
  background: #f6ffed;
}

.stat-card.added .stat-icon {
  background: #52c41a;
  color: #fff;
}

.stat-card.modified {
  background: #e6f7ff;
}

.stat-card.modified .stat-icon {
  background: #1890ff;
  color: #fff;
}

.stat-card.removed {
  background: #fff1f0;
}

.stat-card.removed .stat-icon {
  background: #ff4d4f;
  color: #fff;
}

.stat-icon {
  width: 56px;
  height: 56px;
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
  color: #606266;
}

/* 分析内容 */
.analysis-content {
  line-height: 1.8;
  color: #606266;
}

.analysis-content :deep(h4) {
  margin: 24px 0 16px;
  color: #303133;
  font-size: 16px;
  border-bottom: 1px solid #e4e7ed;
  padding-bottom: 8px;
}

.analysis-content :deep(p) {
  margin: 12px 0;
}

/* 空状态 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
  flex: 1;
  min-height: 400px;
}

.empty-icon {
  font-size: 80px;
  color: #dcdfe6;
  margin-bottom: 20px;
}

.empty-title {
  font-size: 18px;
  color: #303133;
  font-weight: 500;
  margin-bottom: 12px;
}

.empty-desc {
  font-size: 14px;
  color: #909399;
  text-align: center;
  max-width: 400px;
}

/* 加载中 */
.loading-container {
  padding: 40px;
  text-align: center;
}

.loading-text {
  margin-top: 20px;
  color: #909399;
  font-size: 14px;
}

/* 快捷对比模板 */
.templates-card {
  max-width: 600px;
}

.templates-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.template-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
  background: #fff;
}

.template-item:hover {
  border-color: #409eff;
  background: #f5f7fa;
}

.template-icon {
  font-size: 24px;
  color: #409eff;
  flex-shrink: 0;
}

.template-info {
  flex: 1;
  min-width: 0;
}

.template-name {
  font-weight: 500;
  color: #303133;
  margin-bottom: 4px;
  font-size: 14px;
}

.template-desc {
  font-size: 13px;
  color: #909399;
}

.template-arrow {
  font-size: 16px;
  color: #c0c4cc;
  flex-shrink: 0;
}

/* 版本选项样式 */
.version-option {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
}

.version-number {
  font-weight: 600;
  color: #409eff;
  min-width: 40px;
}

.version-name {
  color: #606266;
  flex: 1;
}

.version-stats {
  font-size: 12px;
  color: #909399;
  background: #f5f7fa;
  padding: 2px 8px;
  border-radius: 4px;
}

/* 响应式 */
@media (max-width: 768px) {
  .selector-row {
    flex-direction: column;
    align-items: stretch;
  }

  .vs-label {
    text-align: center;
    padding: 8px 0;
  }

  .stat-card {
    margin-bottom: 12px;
  }
}
</style>
