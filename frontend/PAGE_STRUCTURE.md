# 前端页面源文件结构说明

本文档详细说明了项目的所有前端页面源文件结构。

## 目录结构概览

```
frontend/
├── index.html                      # 入口HTML文件
├── src/
│   ├── App.vue                     # 根组件
│   ├── layout/
│   │   └── index.vue               # 主布局组件
│   ├── components/                 # 公共组件
│   │   ├── JsonTreeNode.vue
│   │   ├── JsonTreeViewer.vue
│   │   ├── MenuTreeItem.vue
│   │   ├── SidebarDropdown.vue
│   │   └── DataFactorySelector.vue
│   └── views/                      # 页面视图组件
│       ├── Home.vue
│       ├── api-testing/
│       ├── app-automation/
│       ├── ui-automation/
│       ├── data-factory/
│       ├── testcases/
│       ├── requirement-analysis/
│       ├── reviews/
│       ├── executions/
│       ├── reports/
│       ├── testsuites/
│       ├── projects/
│       ├── versions/
│       ├── configuration/
│       ├── notification/
│       ├── assistant/
│       ├── auth/
│       └── profile/
```

---

## 页面模块详情

### 1. 首页

| 文件路径 | 说明 |
|---------|------|
| `frontend/src/views/Home.vue` | 系统首页仪表盘 |

---

### 2. API测试模块 (api-testing)

| 文件路径 | 说明 |
|---------|------|
| `frontend/src/views/api-testing/index.vue` | API测试模块主页 |
| `frontend/src/views/api-testing/InterfaceList.vue` | 接口列表页面 |
| `frontend/src/views/api-testing/InterfaceDetail.vue` | 接口详情页面 |
| `frontend/src/views/api-testing/InterfaceManagement.vue` | 接口管理页面 |
| `frontend/src/views/api-testing/AutomationSuiteList.vue` | 自动化套件列表 |
| `frontend/src/views/api-testing/AutomationSuiteDetail.vue` | 自动化套件详情 |
| `frontend/src/views/api-testing/CollectionList.vue` | 测试集合列表 |
| `frontend/src/views/api-testing/EnvironmentManagement.vue` | 环境管理页面 |
| `frontend/src/views/api-testing/ProjectManagement.vue` | 项目管理页面 |
| `frontend/src/views/api-testing/RequestHistory.vue` | 请求历史记录 |
| `frontend/src/views/api-testing/ReportView.vue` | 测试报告视图 |
| `frontend/src/views/api-testing/ScheduledTasks.vue` | 定时任务管理 |
| `frontend/src/views/api-testing/TeamStatistics.vue` | 团队统计数据 |
| `frontend/src/views/api-testing/AIServiceConfig.vue` | AI服务配置 |
| `frontend/src/views/api-testing/ApifoxSceneCheck.vue` | Apifox场景检查 |
| `frontend/src/views/api-testing/NotificationManagement.vue` | 通知管理 |

#### API测试子组件 (components)

| 文件路径 | 说明 |
|---------|------|
| `frontend/src/views/api-testing/components/KeyValueEditor.vue` | 键值对编辑器 |
| `frontend/src/views/api-testing/components/ReportDetail.vue` | 报告详情组件 |
| `frontend/src/views/api-testing/components/SuiteRequestTree.vue` | 套件请求树形结构 |
| `frontend/src/views/api-testing/components/ApifoxImportDialog.vue` | Apifox导入对话框 |
| `frontend/src/views/api-testing/components/ImportDialog.vue` | 通用导入对话框 |
| `frontend/src/views/api-testing/components/RecursiveStep.vue` | 递归步骤组件 |
| `frontend/src/views/api-testing/components/HistoryTable.vue` | 历史记录表格 |
| `frontend/src/views/api-testing/components/JsonTreeNode.vue` | JSON树节点组件 |
| `frontend/src/views/api-testing/components/EnvironmentTable.vue` | 环境变量表格 |

---

### 3. APP自动化模块 (app-automation)

| 文件路径 | 说明 |
|---------|------|
| `frontend/src/views/app-automation/Index.vue` | APP自动化模块主页 |
| `frontend/src/views/app-automation/dashboard/Dashboard.vue` | APP自动化仪表盘 |

#### 测试用例 (test-cases)

| 文件路径 | 说明 |
|---------|------|
| `frontend/src/views/app-automation/test-cases/TestCaseList.vue` | 测试用例列表 |
| `frontend/src/views/app-automation/test-cases/SceneBuilder.vue` | 场景构建器 |

#### 元素管理 (elements)

| 文件路径 | 说明 |
|---------|------|
| `frontend/src/views/app-automation/elements/ElementList.vue` | 元素列表 |
| `frontend/src/views/app-automation/elements/components/CaptureElementDialog.vue` | 捕获元素对话框 |
| `frontend/src/views/app-automation/elements/components/ManualElementDialog.vue` | 手动添加元素对话框 |

#### 套件管理 (suites)

| 文件路径 | 说明 |
|---------|------|
| `frontend/src/views/app-automation/suites/SuiteList.vue` | 套件列表 |

#### 执行管理 (executions)

| 文件路径 | 说明 |
|---------|------|
| `frontend/src/views/app-automation/executions/ExecutionList.vue` | 执行记录列表 |

#### 设备管理 (devices)

| 文件路径 | 说明 |
|---------|------|
| `frontend/src/views/app-automation/devices/DeviceList.vue` | 设备列表管理 |

#### 报告管理 (reports)

| 文件路径 | 说明 |
|---------|------|
| `frontend/src/views/app-automation/reports/ReportList.vue` | 测试报告列表 |

#### 定时任务 (scheduled-tasks)

| 文件路径 | 说明 |
|---------|------|
| `frontend/src/views/app-automation/scheduled-tasks/ScheduledTasks.vue` | 定时任务配置 |

#### 项目管理 (projects)

| 文件路径 | 说明 |
|---------|------|
| `frontend/src/views/app-automation/projects/ProjectList.vue` | 项目列表 |

#### 包管理 (packages)

| 文件路径 | 说明 |
|---------|------|
| `frontend/src/views/app-automation/packages/PackageList.vue` | APP包管理列表 |

#### 通知管理 (notification)

| 文件路径 | 说明 |
|---------|------|
| `frontend/src/views/app-automation/notification/NotificationLogs.vue` | 通知日志 |

#### 设置 (settings)

| 文件路径 | 说明 |
|---------|------|
| `frontend/src/views/app-automation/settings/AppSettings.vue` | APP设置页面 |

---

### 4. UI自动化模块 (ui-automation)

| 文件路径 | 说明 |
|---------|------|
| `frontend/src/views/ui-automation/Index.vue` | UI自动化模块主页 |

#### 测试用例 (test-cases)

| 文件路径 | 说明 |
|---------|------|
| `frontend/src/views/ui-automation/test-cases/TestCaseManager.vue` | 测试用例管理 |

#### 元素管理 (elements)

| 文件路径 | 说明 |
|---------|------|
| `frontend/src/views/ui-automation/elements/ElementList.vue` | 元素列表 |
| `frontend/src/views/ui-automation/elements/ElementManagerEnhanced.vue` | 增强版元素管理器 |

#### 套件管理 (suites)

| 文件路径 | 说明 |
|---------|------|
| `frontend/src/views/ui-automation/suites/SuiteList.vue` | 套件列表 |

#### 执行管理 (executions)

| 文件路径 | 说明 |
|---------|------|
| `frontend/src/views/ui-automation/executions/ExecutionList.vue` | 执行记录列表 |

#### 项目管理 (projects)

| 文件路径 | 说明 |
|---------|------|
| `frontend/src/views/ui-automation/projects/ProjectList.vue` | 项目列表 |
| `frontend/src/views/ui-automation/projects/ProjectDetail.vue` | 项目详情 |

#### 脚本管理 (scripts)

| 文件路径 | 说明 |
|---------|------|
| `frontend/src/views/ui-automation/scripts/ScriptList.vue` | 脚本列表 |
| `frontend/src/views/ui-automation/scripts/ScriptEditorEnhanced.vue` | 增强版脚本编辑器 |

#### 页面对象 (page-objects)

| 文件路径 | 说明 |
|---------|------|
| `frontend/src/views/ui-automation/page-objects/PageObjectManager.vue` | 页面对象管理器 |

#### 报告管理 (reports)

| 文件路径 | 说明 |
|---------|------|
| `frontend/src/views/ui-automation/reports/ReportList.vue` | 测试报告列表 |

#### 定时任务 (scheduled-tasks)

| 文件路径 | 说明 |
|---------|------|
| `frontend/src/views/ui-automation/scheduled-tasks/ScheduledTasks.vue` | 定时任务配置 |

#### 通知管理 (notification)

| 文件路径 | 说明 |
|---------|------|
| `frontend/src/views/ui-automation/notification/NotificationLogs.vue` | 通知日志 |
| `frontend/src/views/ui-automation/notification/NotificationConfigs.vue` | 通知配置 |

#### 仪表盘 (dashboard)

| 文件路径 | 说明 |
|---------|------|
| `frontend/src/views/ui-automation/dashboard/Dashboard.vue` | UI自动化仪表盘 |

#### AI功能 (ai)

| 文件路径 | 说明 |
|---------|------|
| `frontend/src/views/ui-automation/ai/AITesting.vue` | AI测试主页面 |
| `frontend/src/views/ui-automation/ai/AISuiteList.vue` | AI测试套件列表 |
| `frontend/src/views/ui-automation/ai/AICaseList.vue` | AI测试用例列表 |
| `frontend/src/views/ui-automation/ai/AIExecutionRecords.vue` | AI执行记录 |
| `frontend/src/views/ui-automation/ai/AIExecutionReport.vue` | AI执行报告 |
| `frontend/src/views/ui-automation/ai/AIElementLocator.vue` | AI元素定位 |
| `frontend/src/views/ui-automation/ai/XMindConverter.vue` | XMind转换器 |

---

### 5. 数据工厂模块 (data-factory)

| 文件路径 | 说明 |
|---------|------|
| `frontend/src/views/data-factory/DataFactory.vue` | 数据工厂主页 |
| `frontend/src/views/data-factory/BugAnalysis.vue` | Bug分析页面 |
| `frontend/src/views/data-factory/BugAnalysisSummary.vue` | Bug分析汇总 |
| `frontend/src/views/data-factory/ExcelDataFiller.vue` | Excel数据填充工具 |
| `frontend/src/views/data-factory/AIRubricGenerator.vue` | AI评分生成器 |

---

### 6. 测试用例模块 (testcases)

| 文件路径 | 说明 |
|---------|------|
| `frontend/src/views/testcases/TestCaseList.vue` | 测试用例列表 |
| `frontend/src/views/testcases/TestCaseDetail.vue` | 测试用例详情 |
| `frontend/src/views/testcases/TestCaseEdit.vue` | 测试用例编辑 |
| `frontend/src/views/testcases/TestCaseForm.vue` | 测试用例表单 |
| `frontend/src/views/testcases/AuthorTestCaseDetail.vue` | 作者用例详情 |
| `frontend/src/views/testcases/TestCaseStatistics.vue` | 用例统计 |

---

### 7. 需求分析模块 (requirement-analysis)

| 文件路径 | 说明 |
|---------|------|
| `frontend/src/views/requirement-analysis/RequirementAnalysisView.vue` | 需求分析主页 |
| `frontend/src/views/requirement-analysis/KnowledgeGraphOverview.vue` | 知识图谱概览 |
| `frontend/src/views/requirement-analysis/KnowledgeGraphVisualization.vue` | 知识图谱可视化 |
| `frontend/src/views/requirement-analysis/KnowledgeGraphCompare.vue` | 知识图谱对比 |
| `frontend/src/views/requirement-analysis/ProjectDocumentManagement.vue` | 项目文档管理 |
| `frontend/src/views/requirement-analysis/AIModelConfig.vue` | AI模型配置 |
| `frontend/src/views/requirement-analysis/TestTemplateConfig.vue` | 测试模板配置 |
| `frontend/src/views/requirement-analysis/PromptConfig.vue` | 提示词配置 |
| `frontend/src/views/requirement-analysis/GenerationConfigView.vue` | 生成配置视图 |
| `frontend/src/views/requirement-analysis/GeneratedTestCaseList.vue` | 生成的测试用例列表 |
| `frontend/src/views/requirement-analysis/TaskDetail.vue` | 任务详情 |

#### 需求分析子组件 (components)

| 文件路径 | 说明 |
|---------|------|
| `frontend/src/views/requirement-analysis/components/DocumentSelector.vue` | 文档选择器 |
| `frontend/src/views/requirement-analysis/components/ChunkSelector.vue` | 文档块选择器 |
| `frontend/src/views/requirement-analysis/components/ChunkPreview.vue` | 文档块预览 |

---

### 8. 评审模块 (reviews)

| 文件路径 | 说明 |
|---------|------|
| `frontend/src/views/reviews/ReviewList.vue` | 评审列表 |
| `frontend/src/views/reviews/ReviewDetail.vue` | 评审详情 |
| `frontend/src/views/reviews/ReviewForm.vue` | 评审表单 |
| `frontend/src/views/reviews/ReviewTemplateList.vue` | 评审模板列表 |

---

### 9. 执行模块 (executions)

| 文件路径 | 说明 |
|---------|------|
| `frontend/src/views/executions/ExecutionList.vue` | 执行列表 |
| `frontend/src/views/executions/ExecutionListView.vue` | 执行列表视图 |
| `frontend/src/views/executions/ExecutionDetailView.vue` | 执行详情视图 |

---

### 10. 报告模块 (reports)

| 文件路径 | 说明 |
|---------|------|
| `frontend/src/views/reports/ReportList.vue` | 报告列表 |
| `frontend/src/views/reports/AiTestReport.vue` | AI测试报告 |

---

### 11. 测试套件模块 (testsuites)

| 文件路径 | 说明 |
|---------|------|
| `frontend/src/views/testsuites/TestSuiteList.vue` | 测试套件列表 |

---

### 12. 项目管理模块 (projects)

| 文件路径 | 说明 |
|---------|------|
| `frontend/src/views/projects/ProjectList.vue` | 项目列表 |
| `frontend/src/views/projects/ProjectDetail.vue` | 项目详情 |

---

### 13. 版本管理模块 (versions)

| 文件路径 | 说明 |
|---------|------|
| `frontend/src/views/versions/VersionList.vue` | 版本列表 |

---

### 14. 配置中心模块 (configuration)

| 文件路径 | 说明 |
|---------|------|
| `frontend/src/views/configuration/ConfigurationCenter.vue` | 配置中心主页 |
| `frontend/src/views/configuration/AIIntelligentModeConfig.vue` | AI智能模式配置 |
| `frontend/src/views/configuration/DifyConfig.vue` | Dify配置 |
| `frontend/src/views/configuration/UIEnvironmentConfig.vue` | UI环境配置 |

---

### 15. 通知模块 (notification)

| 文件路径 | 说明 |
|---------|------|
| `frontend/src/views/notification/NotificationLogs.vue` | 通知日志 |
| `frontend/src/views/notification/NotificationConfigs.vue` | 通知配置 |

---

### 16. 助手模块 (assistant)

| 文件路径 | 说明 |
|---------|------|
| `frontend/src/views/assistant/AssistantView.vue` | AI助手视图 |
| `frontend/src/views/assistant/KnowledgeBaseView.vue` | 知识库视图 |

---

### 17. 认证模块 (auth)

| 文件路径 | 说明 |
|---------|------|
| `frontend/src/views/auth/Login.vue` | 登录页面 |
| `frontend/src/views/auth/Register.vue` | 注册页面 |

---

### 18. 用户资料模块 (profile)

| 文件路径 | 说明 |
|---------|------|
| `frontend/src/views/profile/UserProfile.vue` | 用户资料页面 |

---

## 公共组件

| 文件路径 | 说明 |
|---------|------|
| `frontend/src/components/JsonTreeNode.vue` | JSON树节点组件 |
| `frontend/src/components/JsonTreeViewer.vue` | JSON树查看器 |
| `frontend/src/components/MenuTreeItem.vue` | 菜单树项目组件 |
| `frontend/src/components/SidebarDropdown.vue` | 侧边栏下拉菜单 |
| `frontend/src/components/DataFactorySelector.vue` | 数据工厂选择器 |

---

## 布局组件

| 文件路径 | 说明 |
|---------|------|
| `frontend/src/layout/index.vue` | 主布局组件（包含侧边栏、顶部导航等） |

---

## 核心入口文件

| 文件路径 | 说明 |
|---------|------|
| `frontend/index.html` | 应用入口HTML文件 |
| `frontend/src/App.vue` | Vue根组件 |
| `frontend/src/main.js` | 应用入口JS文件 |

---

## 技术栈

- **框架**: Vue.js 3.x
- **构建工具**: Vite
- **UI组件库**: Element Plus
- **路由**: Vue Router
- **状态管理**: Pinia/Vuex
- **HTTP客户端**: Axios

---

## 页面统计

| 模块 | 页面数量 | 组件数量 |
|------|---------|---------|
| API测试 | 16 | 9 |
| APP自动化 | 15 | 2 |
| UI自动化 | 18 | 0 |
| 数据工厂 | 5 | 0 |
| 测试用例 | 6 | 0 |
| 需求分析 | 11 | 3 |
| 评审 | 4 | 0 |
| 执行 | 3 | 0 |
| 报告 | 2 | 0 |
| 其他 | 12 | 0 |
| **总计** | **92** | **14** |

---

*文档生成时间: 2026-06-08*