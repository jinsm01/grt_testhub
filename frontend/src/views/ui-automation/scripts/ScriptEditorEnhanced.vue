<template>
  <div class="script-editor-enhanced">
    <div class="page-header">
      <div class="header-actions">
        <el-select v-model="projectId" :placeholder="$t('uiAutomation.common.selectProject')" style="width: 180px" @change="onProjectChange">
          <el-option v-for="project in projects" :key="project.id" :label="project.name" :value="project.id" />
        </el-select>
      </div>
    </div>

    <div class="main-content">
      <!-- 左侧:元素库(页面树形式) -->
      <div class="left-panel">
        <div class="panel-content">
          <div class="tree-search">
            <el-input
              v-model="elementFilter"
              :placeholder="$t('uiAutomation.scriptEditor.searchElement')"
              clearable
              size="default"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
          </div>
          <el-tree
            :key="treeKey"
            ref="elementTreeRef"
            :data="elementTree"
            :filter-node-method="filterElementNode"
            :props="{ children: 'children', label: 'name' }"
            node-key="id"
            default-expand-all
            :expand-on-click-node="false"
            @node-click="handleElementClick"
          >
            <template #default="{ data }">
              <div class="tree-node">
                <el-icon class="node-icon">
                  <component :is="getTreeNodeIcon(data.type)" />
                </el-icon>
                <span class="node-label">{{ data.name }}</span>
              </div>
            </template>
          </el-tree>
        </div>
      </div>

      <!-- 中间:代码编辑器 -->
      <div class="center-panel">
        <div class="code-editor-container">
          <div v-if="editorLoading" class="editor-loading">
            <el-icon class="loading-icon"><Loading /></el-icon>
            <span>正在加载代码编辑器...</span>
          </div>
          <div v-else-if="editorError" class="editor-error">
            <el-icon><Warning /></el-icon>
            <span>代码编辑器加载失败</span>
            <el-button type="primary" size="small" @click="initMonacoEditor">重试</el-button>
          </div>
          <div v-show="!editorLoading && !editorError" ref="monacoEditor" class="monaco-editor"></div>
        </div>
      </div>

      <!-- 右侧:元素详情 -->
      <div class="right-panel">
        <el-tabs v-model="rightActiveTab" v-if="selectedElementDetail">
          <!-- 元素详情 -->
          <el-tab-pane :label="$t('uiAutomation.scriptEditor.elementDetail')" name="elementDetail" v-if="selectedElementDetail">
            <div class="panel-content">
              <div class="element-detail">
                <div class="element-header">
                  <div class="element-icon">
                    <el-icon><Document /></el-icon>
                  </div>
                  <div class="element-title">
                    <h4>{{ selectedElementDetail.name }}</h4>
                    <span class="element-subtitle">{{ selectedElementDetail.page || $t('uiAutomation.element.notSpecified') }} · {{ getElementTypeText(selectedElementDetail.element_type) }}</span>
                  </div>
                </div>

                <div class="element-info-list">
                  <div class="info-item">
                    <span class="info-label">{{ $t('uiAutomation.scriptEditor.locatorStrategy') }}</span>
                    <span class="info-value strategy-tag">{{ selectedElementDetail.locator_strategy?.name || selectedElementDetail.locator_strategy }}</span>
                  </div>
                  <div class="info-item">
                    <span class="info-label">{{ $t('uiAutomation.scriptEditor.locatorExpression') }}</span>
                    <code class="info-code">{{ selectedElementDetail.locator_value }}</code>
                  </div>
                  <div class="info-item">
                    <span class="info-label">编程语言</span>
                    <el-select v-model="scriptLanguage" size="small" style="width: 110px">
                      <el-option label="JavaScript" value="javascript" />
                      <el-option label="Python" value="python" />
                    </el-select>
                  </div>
                  <div class="info-item">
                    <span class="info-label">测试框架</span>
                    <el-select v-model="scriptFramework" size="small" style="width: 110px">
                      <el-option label="Playwright" value="playwright" />
                      <el-option label="Selenium" value="selenium" />
                    </el-select>
                  </div>
                </div>

                <div class="element-actions">
                  <el-button @click="insertElementCode(selectedElementDetail)">
                    <el-icon><Plus /></el-icon>
                    {{ $t('uiAutomation.scriptEditor.insertCode') }}
                  </el-button>
                  <el-button @click="validateElement(selectedElementDetail)">
                    <el-icon><Check /></el-icon>
                    {{ $t('uiAutomation.scriptEditor.validateElement') }}
                  </el-button>
                </div>

                <div class="code-actions">
                  <el-button size="default" @click="formatCode">
                    <el-icon><Operation /></el-icon>
                    {{ $t('uiAutomation.scriptEditor.format') }}
                  </el-button>
                  <el-button size="default" @click="clearCode">
                    <el-icon><Delete /></el-icon>
                    {{ $t('uiAutomation.scriptEditor.clear') }}
                  </el-button>
                </div>

                <div class="save-action">
                  <el-button size="default" @click="saveScript" :loading="saving" class="save-script-btn">
                    <el-icon><Check /></el-icon>
                    {{ $t('uiAutomation.scriptEditor.saveScript') }}
                  </el-button>
                </div>
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
        <div v-else class="right-panel-empty">
          <el-icon><Document /></el-icon>
          <span>选择元素查看详情</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch, onBeforeUnmount, shallowRef } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Search, Plus, View, Document, Check, Delete, Operation, Folder, Loading, Warning
} from '@element-plus/icons-vue'
import * as monaco from 'monaco-editor'
import editorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker'
import jsonWorker from 'monaco-editor/esm/vs/language/json/json.worker?worker'
import cssWorker from 'monaco-editor/esm/vs/language/css/css.worker?worker'
import htmlWorker from 'monaco-editor/esm/vs/language/html/html.worker?worker'
import tsWorker from 'monaco-editor/esm/vs/language/typescript/ts.worker?worker'

import {
  getUiProjects,
  getTestScripts,
  getElements,
  getElementGroupTree,
  validateElementLocator,
  createTestScript
} from '@/api/ui_automation'

// i18n
const { t } = useI18n()

// 响应式数据
const projects = ref([])
const projectId = ref('')
const scriptContent = ref('')
const scriptLanguage = ref('python')
const scriptFramework = ref('playwright')

const elementTree = ref([])
const elementTreeRef = ref(null)
const elementFilter = ref('')
const selectedElementDetail = ref(null)
const executionLogs = ref([])
const treeKey = ref(0)

const cursorPosition = reactive({ line: 1, column: 1 })
const saving = ref(false)
const editorLoading = ref(true)
const editorError = ref(false)

// 标签页控制
const rightActiveTab = ref('logs')

// Monaco编辑器实例
const monacoEditor = ref(null)
const editor = shallowRef(null)
const monacoRef = shallowRef(null)

// 方法定义
const loadProjects = async () => {
  try {
    const response = await getUiProjects({ page_size: 100 })
    projects.value = response.data.results || response.data
  } catch (error) {
    ElMessage.error(t('uiAutomation.scriptEditor.messages.loadProjectsFailed'))
    console.error('Failed to load projects:', error)
  }
}

const loadElementTree = async () => {
  if (!projectId.value) {
    elementTree.value = []
    return
  }

  try {
    // 加载页面树
    const pageGroupResponse = await getElementGroupTree({ project: projectId.value })
    
    // 构建页面节点
    const buildTree = (groups) => {
      return groups.map(group => ({
        ...group,
        type: 'page',
        children: group.children ? buildTree(group.children) : []
      }))
    }

    const pageNodes = buildTree(pageGroupResponse.data || [])

    console.log('=== Smart Script Generator - Loading Element Tree ===')
    console.log('Page nodes count:', pageNodes.length)

    // 递归查找页面节点的辅助函数
    const findPageNode = (nodes, pageName) => {
      for (const node of nodes) {
        if (node.type === 'page' && node.name === pageName) {
          return node
        }
        if (node.children) {
          const found = findPageNode(node.children, pageName)
          if (found) return found
        }
      }
      return null
    }

    // 加载元素列表
    const elementsResponse = await getElements({ project: projectId.value, page_size: 1000 })
    const elements = elementsResponse.data?.results || elementsResponse.data || []
    console.log('Elements count:', elements.length)

    // 将元素添加到对应页面下
    elements.forEach(element => {
      const pageNode = findPageNode(pageNodes, element.page)
      if (pageNode) {
        if (!pageNode.children) {
          pageNode.children = []
        }
        // 检查是否已存在
        const exists = pageNode.children.some(child => child.id === element.id && child.type === 'element')
        if (!exists) {
          pageNode.children.push({
            ...element,
            type: 'element',
            name: element.name
          })
        }
      }
    })

    elementTree.value = pageNodes
    treeKey.value++ // 强制刷新树组件
    console.log('Final element tree:', JSON.parse(JSON.stringify(pageNodes)))
    console.log('Total elements in tree:', countElements(pageNodes))
  } catch (error) {
    console.error('Failed to load element tree:', error)
  }
}

// 统计元素数量
const countElements = (tree) => {
  let count = 0
  const traverse = (nodes) => {
    nodes.forEach(node => {
      if (node.type === 'element') count++
      if (node.children) traverse(node.children)
    })
  }
  traverse(tree)
  return count
}

// 配置 Monaco Editor workers
if (typeof self !== 'undefined') {
  self.MonacoEnvironment = {
    getWorker(_, label) {
      if (label === 'json') {
        return new jsonWorker()
      }
      if (label === 'css' || label === 'scss' || label === 'less') {
        return new cssWorker()
      }
      if (label === 'html' || label === 'handlebars' || label === 'razor') {
        return new htmlWorker()
      }
      if (label === 'typescript' || label === 'javascript') {
        return new tsWorker()
      }
      return new editorWorker()
    }
  }
}

// 初始化 Monaco Editor
const initMonacoEditor = async () => {
  if (!monacoEditor.value) return

  editorLoading.value = true
  editorError.value = false

  try {
    monacoRef.value = monaco

    editor.value = monaco.editor.create(monacoEditor.value, {
      value: scriptContent.value,
      language: scriptLanguage.value === 'javascript' ? 'javascript' : 'python',
      theme: 'vs-dark',
      fontSize: 15,
      lineHeight: 24,
      minimap: { enabled: false },
      scrollBeyondLastLine: false,
      automaticLayout: true,
      padding: { top: 16, bottom: 16 },
      lineNumbers: 'on',
      renderLineHighlight: 'line',
      selectOnLineNumbers: true,
      cursorStyle: 'line',
      cursorBlinking: 'blink',
      smoothScrolling: true,
      contextmenu: true,
      quickSuggestions: true,
      wordBasedSuggestions: 'currentDocument',
      suggestOnTriggerCharacters: true,
      acceptSuggestionOnEnter: 'on',
      tabCompletion: 'on',
      wordWrap: 'on',
      folding: true,
      renderWhitespace: 'selection',
      bracketPairColorization: { enabled: true }
    })

    // 监听内容变化
    editor.value.onDidChangeModelContent(() => {
      scriptContent.value = editor.value.getValue()
      updateCursorPosition()
    })

    // 监听光标位置变化
    editor.value.onDidChangeCursorPosition((e) => {
      cursorPosition.line = e.position.lineNumber
      cursorPosition.column = e.position.column
    })

    editorLoading.value = false
  } catch (error) {
    console.error('Failed to initialize Monaco Editor:', error)
    editorLoading.value = false
    editorError.value = true
    ElMessage.error('代码编辑器加载失败，请刷新页面重试')
  }
}

// 更新编辑器语言
const updateEditorLanguage = () => {
  if (editor.value) {
    const model = editor.value.getModel()
    if (model) {
      monaco.editor.setModelLanguage(model, scriptLanguage.value === 'javascript' ? 'javascript' : 'python')
    }
  }
}

const handleEditorFocus = () => {
  // 编辑器获得焦点时的处理
}

const handleEditorBlur = () => {
  // 编辑器失去焦点时的处理
}

const handleContentChange = () => {
  // 内容变化时更新状态
  updateCursorPosition()
}

const updateCursorPosition = () => {
  if (editor.value) {
    const position = editor.value.getPosition()
    if (position) {
      cursorPosition.line = position.lineNumber
      cursorPosition.column = position.column
    }
  }
}

const onProjectChange = async () => {
  selectedElementDetail.value = null
  executionLogs.value = []
  scriptContent.value = ''

  await loadElementTree()

  // 代码编辑器已更新(使用 textarea)
}

const filterElementNode = (value, data) => {
  if (!value) return true
  return data.name.indexOf(value) !== -1
}

const handleElementClick = (data) => {
  if (data.type === 'element') {
    selectedElementDetail.value = data
    rightActiveTab.value = 'elementDetail'
  }
}

const showElementDetail = (element) => {
  selectedElementDetail.value = element
  rightActiveTab.value = 'elementDetail'
}

const insertElementCode = (element) => {
  if (element.type !== 'element') return

  const code = generateElementCode(element)
  insertCodeAtCursor(code + '\n')  // 自动换行

  ElMessage.success(`${t('uiAutomation.scriptEditor.messages.insertCode')}: ${element.name}`)
}

const insertCodeAtCursor = (code) => {
  if (!editor.value) return

  // 获取当前光标位置，如果没有则默认在第一行第一列
  let position = editor.value.getPosition()
  if (!position) {
    position = { lineNumber: 1, column: 1 }
  }

  // 如果编辑器为空，从第一行开始插入
  const model = editor.value.getModel()
  const isEmpty = model && model.getLineCount() === 1 && model.getLineContent(1) === ''

  if (isEmpty) {
    // 空编辑器时直接设置值
    editor.value.setValue(code)
  } else {
    // 非空时在光标位置插入
    editor.value.executeEdits('insert-element', [{
      range: new monaco.Range(position.lineNumber, position.column, position.lineNumber, position.column),
      text: code
    }])
  }

  // 移动光标到插入代码之后
  const lines = code.split('\n')
  const newLineNumber = position.lineNumber + lines.length - 1
  const newColumn = lines.length === 1
    ? (isEmpty ? code.length + 1 : position.column + code.length)
    : lines[lines.length - 1].length + 1

  editor.value.setPosition({ lineNumber: newLineNumber, column: newColumn })
  editor.value.focus()

  // 同步更新 scriptContent
  scriptContent.value = editor.value.getValue()
}

const generateElementCode = (element) => {
  const locatorValue = element.locator_value || ''
  const locatorStrategy = element.locator_strategy?.name || element.locator_strategy || 'css'

  if (scriptLanguage.value === 'javascript') {
    switch (scriptFramework.value) {
      case 'playwright':
        return `await page.locator('${locatorValue}').click();`
      case 'selenium':
        return `await driver.findElement(By.${locatorStrategy.toUpperCase()}('${locatorValue}')).click();`
      default:
        return `await page.locator('${locatorValue}').click();`
    }
  } else {
    switch (scriptFramework.value) {
      case 'playwright':
        return `page.locator('${locatorValue}').click()`
      case 'selenium':
        return `driver.find_element(By.${locatorStrategy.toUpperCase()}, '${locatorValue}').click()`
      default:
        return `page.locator('${locatorValue}').click()`
    }
  }
}

// 生成脚本文件名
const generateScriptName = () => {
  const currentProject = projects.value.find(p => p.id === projectId.value)
  const projectName = currentProject?.name || 'Script'
  const language = scriptLanguage.value === 'javascript' ? 'JS' : 'Python'
  const framework = scriptFramework.value === 'playwright' ? 'Playwright' : 'Selenium'
  const date = new Date()
  const dateStr = `${date.getFullYear()}${String(date.getMonth() + 1).padStart(2, '0')}${String(date.getDate()).padStart(2, '0')}`

  // 获取自增数字 - 简单实现，实际应从后端获取
  const timestamp = Date.now() % 1000

  const extension = scriptLanguage.value === 'javascript' ? 'js' : 'py'

  return `${projectName}_${language}_${framework}_${dateStr}_${timestamp}.${extension}`
}

const saveScript = async () => {
  if (!projectId.value) {
    ElMessage.warning(t('uiAutomation.scriptEditor.messages.selectProject'))
    return
  }

  if (!scriptContent.value.trim()) {
    ElMessage.warning(t('uiAutomation.scriptEditor.messages.emptyScript'))
    return
  }

  let scriptName = ''
  try {
    const result = await ElMessageBox.prompt(
      '',
      '保存脚本',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        inputPlaceholder: '请输入脚本名称',
        customClass: 'script-save-message-box',
        inputValidator: (value) => {
          if (!value || !value.trim()) {
            return '脚本名称不能为空'
          }
          return true
        }
      }
    )
    // @ts-ignore
    scriptName = result.value || ''
  } catch {
    // 用户取消
    return
  }

  if (!scriptName) {
    return
  }

  saving.value = true

  try {
    await createTestScript({
      name: scriptName.trim(),
      project: projectId.value,
      script_type: 'CODE',
      content: scriptContent.value,
      language: scriptLanguage.value,
      framework: scriptFramework.value
    })

    ElMessage.success(`${t('uiAutomation.scriptEditor.messages.saveSuccess')}: ${scriptName}`)
  } catch (error) {
    console.error('Failed to save script:', error)
    ElMessage.error(t('uiAutomation.scriptEditor.messages.saveFailed'))
  } finally {
    saving.value = false
  }
}

const validateElement = async (element) => {
  try {
    const response = await validateElementLocator(element.id)
    const result = response.data

    if (result.is_valid) {
      ElMessage.success(t('uiAutomation.scriptEditor.messages.validatePassed'))
    } else {
      ElMessage.error(`${t('uiAutomation.scriptEditor.messages.validateFailed')}: ${result.validation_message}`)
    }
  } catch (error) {
    console.error('Failed to validate element:', error)
    ElMessage.error(t('uiAutomation.scriptEditor.messages.validateFailed'))
  }
}

const formatCode = () => {
  // 使用 Monaco Editor 的格式化功能
  try {
    if (editor.value) {
      editor.value.getAction('editor.action.formatDocument').run()
      ElMessage.success(t('uiAutomation.scriptEditor.messages.codeFormatted'))
    }
  } catch (error) {
    ElMessage.error(t('uiAutomation.scriptEditor.messages.formatFailed'))
  }
}

const clearCode = () => {
  scriptContent.value = ''
  if (editor.value) {
    editor.value.setValue('')
  }
  ElMessage.success(t('uiAutomation.scriptEditor.messages.codeCleared'))
}

// 辅助方法
const getTreeNodeIcon = (type) => {
  return type === 'page' ? Folder : Document
}

const getElementTypeText = (type) => {
  const typeMap = {
    'BUTTON': t('uiAutomation.element.elementTypes.button'),
    'INPUT': t('uiAutomation.element.elementTypes.input'),
    'LINK': t('uiAutomation.element.elementTypes.link'),
    'DROPDOWN': t('uiAutomation.element.elementTypes.dropdown'),
    'CHECKBOX': t('uiAutomation.element.elementTypes.checkbox'),
    'RADIO': t('uiAutomation.element.elementTypes.radio'),
    'TEXT': t('uiAutomation.element.elementTypes.text'),
    'IMAGE': t('uiAutomation.element.elementTypes.image'),
    'CONTAINER': t('uiAutomation.element.elementTypes.container'),
    'TABLE': t('uiAutomation.element.elementTypes.table'),
    'FORM': t('uiAutomation.element.elementTypes.form'),
    'MODAL': t('uiAutomation.element.elementTypes.modal')
  }
  return typeMap[type] || type
}

const formatTime = (timestamp) => {
  return timestamp.toLocaleTimeString()
}

// 监听器
watch(elementFilter, (val) => {
  if (elementTreeRef.value) {
    elementTreeRef.value.filter(val)
  }
})

watch(scriptLanguage, (newLang) => {
  updateEditorLanguage()
})

// 组件挂载
onMounted(async () => {
  await loadProjects()

  if (projects.value.length > 0) {
    projectId.value = projects.value[0].id
    await onProjectChange()
  }

  // 初始化 Monaco Editor
  initMonacoEditor()
})

// 组件卸载前清理
onBeforeUnmount(() => {
  if (editor.value) {
    editor.value.dispose()
    editor.value = null
  }
})
</script>

<style scoped lang="scss">
.script-editor-enhanced {
  padding: 24px;
  min-height: calc(100vh - 60px);
  background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%);
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.page-header {
  background: #ffffff;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 4px 20px rgba(147, 112, 219, 0.1);
  display: flex;
  justify-content: space-between;
  align-items: center;
  border: 1px solid rgba(147, 112, 219, 0.1);

  .page-title {
    margin: 0;
    font-size: 24px;
    font-weight: 600;
    color: #5a32a3;
    background: linear-gradient(135deg, #5a32a3 0%, #7b42f6 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  .header-actions {
    display: flex;
    align-items: center;
    gap: 8px;

    .toolbar-divider {
      width: 1px;
      height: 24px;
      background: rgba(147, 112, 219, 0.2);
      margin: 0 4px;
    }

    .flex-spacer {
      flex: 1;
    }

    :deep(.el-input__wrapper) {
      border-radius: 6px;
      border: 1px solid rgba(147, 112, 219, 0.25);
      box-shadow: none;

      &:hover, &.is-focus {
        border-color: #7b42f6;
        box-shadow: 0 0 0 2px rgba(123, 66, 246, 0.08);
      }
    }

    :deep(.el-button) {
      border-radius: 6px;
    }

    :deep(.el-button--primary) {
      background: #7b42f6;
      border-color: #7b42f6;

      &:hover {
        background: #6d33e6;
        border-color: #6d33e6;
      }
    }
  }
}

.main-content {
  flex: 1;
  display: flex;
  overflow: hidden;
  background: #ffffff;
  border-radius: 16px;
  margin-top: 16px;
  box-shadow: 0 4px 20px rgba(147, 112, 219, 0.08);
}

.left-panel {
  width: 320px;
  display: flex;
  flex-direction: column;
  background: #ffffff;
  border-right: 1px solid rgba(147, 112, 219, 0.1);
  overflow: hidden;

  .panel-content {
    padding: 16px;
    flex: 1;
    overflow-y: auto;
    display: flex;
    flex-direction: column;

    .tree-search {
      margin-bottom: 12px;
      flex-shrink: 0;

      :deep(.el-input__wrapper) {
        border-radius: 6px;
        box-shadow: 0 0 0 1px rgba(147, 112, 219, 0.15) inset;

        &:hover {
          box-shadow: 0 0 0 1px rgba(123, 66, 246, 0.3) inset;
        }

        &.is-focus {
          box-shadow: 0 0 0 1px #7b42f6 inset;
        }
      }
    }

    :deep(.el-tree) {
      background: transparent;
      flex: 1;
      overflow-y: auto;

      .el-tree-node__content {
        border-radius: 8px;
        margin-bottom: 4px;
        padding: 10px 12px;
        transition: all 0.2s ease;
        min-height: 40px;

        &:hover {
          background: rgba(123, 66, 246, 0.06);
        }
      }

      .el-tree-node.is-current > .el-tree-node__content {
        background: rgba(123, 66, 246, 0.1);
      }

      .el-tree-node__expand-icon {
        font-size: 14px;
        margin-right: 6px;
      }

      .el-tree-node__children {
        padding-left: 16px;
      }
    }
  }
}

.center-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: #1e1e1e;
  border-right: 1px solid transparent;
  overflow: hidden;
}

.right-panel {
  width: 300px;
  display: flex;
  flex-direction: column;
  background: #ffffff;
  overflow: hidden;

  :deep(.el-tabs) {
    flex: 1;
    display: flex;
    flex-direction: column;
    border: none;
    background: #ffffff;
    overflow: hidden;

    .el-tabs__header {
      display: none;
    }

    .el-tabs__content {
      flex: 1;
      overflow: hidden;
      padding: 0;

      .el-tab-pane {
        height: 100%;
        overflow: hidden;
      }
    }
  }
}

.panel-content {
  padding: 15px;
  flex: 1;
  overflow-y: auto;
}



.code-editor-container {
  flex: 1;
  position: relative;
  background: #1e1e1e;
  overflow: hidden;

  .monaco-editor {
    width: 100%;
    height: 100%;
  }

  .editor-loading,
  .editor-error {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 16px;
    color: #fff;
    font-size: 14px;
    background: #1e1e1e;
    z-index: 10;

    .el-icon {
      font-size: 32px;
      color: #7b42f6;
    }

    .loading-icon {
      animation: rotate 1s linear infinite;
    }
  }

  .editor-error {
    .el-icon {
      color: #f56c6c;
    }
  }
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.editor-status {
  display: none;
}

.tree-node {
  display: flex;
  align-items: center;
  flex: 1;
  justify-content: space-between;
  font-size: 14px;
  padding: 6px 10px;
  border-radius: 8px;
  transition: all 0.2s ease;
  min-height: 32px;
}

.node-icon {
  margin-right: 10px;
  font-size: 16px;
  color: #7b42f6;
}

.node-label {
  flex: 1;
  color: #444;
  font-weight: 500;
  line-height: 1.4;
}

.node-actions {
  display: flex;
  gap: 6px;
  margin-left: 8px;

  .el-button {
    padding: 4px 8px;
    height: 28px;
    border-radius: 6px;

    &:hover {
      background: rgba(123, 66, 246, 0.1);
      color: #7b42f6;
    }

    .el-icon {
      font-size: 14px;
    }
  }
}

.right-panel-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: #aaa;
  gap: 12px;
  background: #ffffff;

  .el-icon {
    font-size: 40px;
    opacity: 0.4;
  }

  span {
    font-size: 13px;
  }
}

.element-detail {
  padding: 16px;
  background: #ffffff;
  height: 100%;
  overflow-y: auto;

  .element-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 16px;
    padding: 12px;
    background: #f8f7fc;
    border-radius: 8px;

    .element-icon {
      width: 36px;
      height: 36px;
      border-radius: 6px;
      background: linear-gradient(135deg, #7b42f6 0%, #9a6df7 100%);
      display: flex;
      align-items: center;
      justify-content: center;
      color: #fff;
      font-size: 16px;
    }

    .element-title {
      flex: 1;

      h4 {
        margin: 0 0 2px 0;
        color: #333;
        font-weight: 600;
        font-size: 14px;
        line-height: 1.4;
      }

      .element-subtitle {
        color: #888;
        font-size: 11px;
      }
    }
  }

  .element-info-list {
    display: flex;
    flex-direction: column;
    gap: 8px;

    .info-item {
      display: flex;
      flex-direction: column;
      gap: 4px;
      padding: 10px 12px;
      background: #f8f7fc;
      border-radius: 6px;

      .info-label {
        color: #999;
        font-size: 11px;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
      }

      .info-value {
        color: #333;
        font-size: 13px;
        font-weight: 500;

        &.strategy-tag {
          display: inline-block;
          background: rgba(123, 66, 246, 0.1);
          color: #7b42f6;
          padding: 4px 10px;
          border-radius: 4px;
          font-size: 11px;
          font-weight: 600;
          width: fit-content;
        }

        &.usage-count {
          color: #7b42f6;
          font-weight: 600;
          font-size: 15px;
        }
      }

      .info-code {
        background: linear-gradient(135deg, #f8f5ff 0%, #f0e6ff 100%);
        color: #5a2db0;
        padding: 10px 12px;
        border-radius: 8px;
        font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
        font-size: 12px;
        word-break: break-all;
        line-height: 1.5;
        border: 1px solid rgba(123, 66, 246, 0.2);
        box-shadow: 0 2px 4px rgba(123, 66, 246, 0.05);
        display: block;
        margin-top: 6px;
      }
    }
  }
}

.element-actions {
  display: flex;
  gap: 8px;
  margin-top: 16px;

  .el-button {
    flex: 1;
    border-radius: 6px;
    transition: all 0.2s ease;
    font-size: 12px;
    padding: 8px 12px;
    height: 36px;
    border: 1px solid rgba(147, 112, 219, 0.25);
    color: #666;
    background: #ffffff;

    .el-icon {
      font-size: 13px;
      margin-right: 6px;
    }

    &:hover {
      border-color: #7b42f6;
      color: #7b42f6;
      background: #ffffff;
    }

    &:active {
      background: #7b42f6;
      border-color: #7b42f6;
      color: #ffffff;
    }
  }
}

.code-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(147, 112, 219, 0.1);

  .el-button {
    flex: 1;
    border-radius: 6px;
    transition: all 0.2s ease;
    font-size: 12px;
    padding: 8px 12px;
    height: 36px;
    border: 1px solid rgba(147, 112, 219, 0.25);
    color: #666;
    background: #ffffff;

    .el-icon {
      font-size: 13px;
      margin-right: 6px;
    }

    &:hover {
      border-color: #7b42f6;
      color: #7b42f6;
      background: #ffffff;
    }

    &:active {
      background: #7b42f6;
      border-color: #7b42f6;
      color: #ffffff;
    }
  }
}

.save-action {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid rgba(147, 112, 219, 0.15);

  .save-script-btn {
    width: 100%;
    height: 40px;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 500;
    background: linear-gradient(135deg, #7b42f6 0%, #9d5cf6 100%);
    border: none;
    color: #ffffff;
    box-shadow: 0 4px 12px rgba(123, 66, 246, 0.25);
    transition: all 0.3s ease;

    &:hover {
      background: linear-gradient(135deg, #6d33e6 0%, #8d4de6 100%);
      box-shadow: 0 6px 16px rgba(123, 66, 246, 0.35);
      transform: translateY(-1px);
    }

    &:active {
      transform: translateY(0);
      box-shadow: 0 2px 8px rgba(123, 66, 246, 0.25);
    }

    .el-icon {
      font-size: 16px;
      margin-right: 6px;
    }
  }
}

:deep(.el-message-box) {
  width: 420px !important;

  .el-message-box__content {
    padding-top: 20px;
    padding-bottom: 20px;
  }

  .el-message-box__input {
    padding-top: 0;

    .el-input {
      width: 100% !important;
    }

    .el-input__inner {
      width: 100% !important;
    }

    .el-input__wrapper {
      padding: 8px 15px;
    }
  }

  .el-message-box__status {
    display: none;
  }
}
</style>

<style>
.script-save-message-box {
  width: 420px !important;
}

.script-save-message-box .el-message-box__input {
  width: 100% !important;
}

.script-save-message-box .el-message-box__input .el-input {
  width: 100% !important;
}

.script-save-message-box .el-message-box__input .el-input__wrapper {
  padding: 8px 15px !important;
}
</style>
