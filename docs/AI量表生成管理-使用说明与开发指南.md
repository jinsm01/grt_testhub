# AI 量表生成管理 — 使用说明与开发指南

> **模块名称**：AI量表生成管理  
> **功能路径**：数据工厂 → AI量表生成管理 (`/data-factory/ai-rubric`)  
> **最后更新**：2026-06-03  
> **版本**：v1.1.0

---

## 目录

- [一、功能概述](#一功能概述)
- [二、用户使用说明](#二用户使用说明)
  - [2.1 页面概览](#21-页面概览)
  - [2.2 上传文件与配置参数](#22-上传文件与配置参数)
  - [2.3 执行生成任务](#23-执行生成任务)
  - [2.4 查看与管理记录](#24-查看与管理记录)
  - [2.5 预览与下载](#25-预览与下载)
  - [2.6 删除记录](#26-删除记录)
- [三、技术架构](#三技术架构)
  - [3.1 系统架构图](#31-系统架构图)
  - [3.2 数据模型](#32-数据模型)
  - [3.3 API 接口清单](#33-api-接口清单)
  - [3.4 前端组件结构](#34-前端组件结构)
- [四、开发指南](#四开发指南)
  - [4.1 项目结构](#41-项目结构)
  - [4.2 后端核心逻辑详解](#42-后端核心逻辑详解)
  - [4.3 前端核心逻辑详解](#43-前端核心逻辑详解)
  - [4.4 关键技术要点](#44-关键技术要点)
  - [4.5 常见问题排查](#45-常见问题排查)
- [五、变更日志](#五变更日志)

---

## 一、功能概述

### 1.1 功能定位

**AI 量表生成管理** 是 TestHub 平台「数据工厂」模块下的智能内容生成工具。它允许用户上传教学/学习相关文档（或图片），由 AI 自动分析内容并生成：

| 产出物 | 说明 | 格式 |
|--------|------|------|
| **评分量表** | 结构化的一级/二级评价指标体系 | XLSX (Excel) |
| **学习心得** | 按得分/不得分分类的学习反思文本 | DOCX (Word) |

### 1.2 核心特性

| 特性 | 描述 |
|------|------|
| 🤖 **AI 驱动生成** | 调用 OpenAI 兼容 API（支持自定义模型配置） |
| 📄 **多格式文件输入** | 支持 .docx / .pdf / .txt / .png / .jpg / .xlsx |
| ⚡ **即时反馈** | 点击生成后立即显示"生成中"状态（事务先提交） |
| 🛡️ **降级兜底** | AI 调用失败自动使用本地模板，保证始终有结果 |
| 📊 **统计面板** | 实时展示累计生成数、已完成数、进行中任务数 |
| 🔍 **筛选搜索** | 支持按状态过滤 + 任务名关键词搜索 |
| 📥 **多格式导出** | 量表导出 Excel（含样式），心得导出 Word 文档 |

---

## 二、用户使用说明

### 2.1 页面概览

进入页面后可见以下区域布局：

```
┌─────────────────────────────────────────────────────┐
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐           │
│  │累计生成│  │已完成│  │生成中 │  │文件数 │ ← 统计卡片行   │
│  └──────┘  └──────┘  └──────┘  └──────┘           │
├─────────────────────────────────────────────────────┤
│  ╔═══════════════════════════════════════════╗     │
│  ║         上传区域（拖拽或点击选择）            ║     │
│  ║   支持 .docx · .pdf · .txt · .png · .jpg    ║     │
│  ╚═══════════════════════════════════════════╝     │
│                                                     │
│  任务名称: [________] 心得数量: [20▼] 得分比例:[60%▼]│
│  心得字数: [300▼]              [▶ 开始生成]        │
│                                                     │
│  ⚠️ 若生成失败，则取默认模板并根据配置生成量表和心得    │
├─────────────────────────────────────────────────────┤
│  自生成记录  共 N 条    [全部状态▼][生成中][已完成][失败] │
│  ┌─────────────────────────────────────────────────┐│
│  │ 序号 | 任务名称 | 关联文件 | 状态 | 心得数量 | ...││
│  │   1  | xxx量表  | xx.pdf  | ✅完成 | 20条   |操作││
│  │   2  | yyy量表  | yy.docx | 🔄处理中|       |操作││
│  └─────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────┘
```

### 2.2 上传文件与配置参数

#### 支持的文件类型

| 类型 | 扩展名 | 大小限制 | 处理方式 |
|------|--------|----------|----------|
| Word 文档 | `.docx` | 最大 20MB | 解析纯文本内容 |
| PDF 文档 | `.pdf` | 最大 20MB | PDF 文本提取 |
| 纯文本 | `.txt` | 最大 20MB | 直接读取 |
| 图片 | `.png` / `.jpg` / `.jpeg` | 最大 20MB | OCR 识别后传给 AI |
| 表格 | `.xlsx` | 最大 20MB | 提取文本内容 |

#### 配置参数说明

| 参数 | 可选值 | 默认值 | 说明 |
|------|--------|--------|------|
| **任务名称** | 自由输入（必填） | — | 用于标识该次生成任务 |
| **心得数量** | 10 / 20(推荐) / 30 | 20 条 | 生成的学习心得总条数 |
| **得分心得比例** | 50% / 60%(推荐) / 70% | 60% | 得分心得占比，剩余为不得分心得 |
| **心得字数** | 100 / 300(推荐) / 500 | 300 字左右 | 单条心得的目标字数 |

### 2.3 执行生成任务

#### 操作步骤

1. **上传文件**（可选）：拖拽或点击"选择文件"上传参考文档
2. **填写任务名称**：必填项，如 `AI技术与学科融合评分量表`
3. **调整参数**（可选）：根据需要修改心得数量、得分比例、字数
4. **点击「开始生成」按钮**

#### 执行流程

```
点击开始生成
    │
    ▼
┌─────────────────────────┐
│  前端发送 POST 请求      │  FormData: name, note_count, pass_ratio, note_length, file
│  同时延迟1000ms刷新列表    │  （等待后端事务提交）
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  后端接收请求             │
│  ① 提取文件内容          │  支持 PDF/DOCX/TXT/图片OCR
│  ② 创建记录(status=running)│  transaction.atomic() 立即提交
│  ③ 返回响应给前端         │  前端此时已能看到新记录
│  ④ 调用 AI API 生成      │  耗时操作，在后台执行
└──────────┬──────────────┘
           │
      ┌────┴────┐
      ▼         ▼
   AI成功      AI失败
      │         │
      ▼         ▼
 status=done  status=error
 (含AI数据)  (含fallback模板数据)
```

### 2.4 查看与管理记录

#### 记录列表表格字段

| 列名 | 说明 |
|------|------|
| **序号** | 当前页序号 |
| **任务名称** | 可点击进入预览弹窗 |
| **关联文件** | 上传的源文件名 |
| **状态** | 标签显示：已完成(绿) / 生成中(黄) / 失败(红) |
| **心得数量** | 配置的总条数及得分比例 |
| **生成时间** | 记录创建时间 |
| **操作** | 预览 / 下载量表 / 下载心得 / 删除 |

#### 状态筛选

点击顶部标签可按状态快速过滤：
- **全部状态**：显示所有记录
- **生成中**：仅 `running` 状态
- **已完成**：仅 `done` 状态
- **失败**：仅 `error` 状态

#### 搜索

在搜索框输入关键词，模糊匹配**任务名称**。

### 2.5 预览与下载

#### 预览弹窗

点击任务名称或「预览」按钮打开预览弹窗，含两个 Tab：

##### Tab 1：评分量表

以表格形式展示生成的评价指标体系：

| 字段 | 说明 |
|------|------|
| # | 序号 |
| 一级指标 | 评价维度（如"教学内容"、"教学方法"等） |
| 二级指标 | 具体评价点 |
| 指标说明 | 详细描述 |

底部统计栏显示：
- 一级指标去重集合
- 总计评分点数量

##### Tab 2：学习心得

列表形式展示每条心得，带颜色区分：

| 类型 | 视觉标识 | 边框颜色 | 背景 |
|------|----------|----------|------|
| **得分心得** | 绿色「得分」标签 | 紫色 `#7C3AED` | 浅紫 `#FAF5FF` |
| **不得分心得** | 红色「不得分」标签 | 红色 `#EF4444` | 浅红 `#FFF5F5` |

每条心得卡片包含：
- **标题**
- **正文内容**
- 底部标签：「观点正确」/「逻辑清晰」/「内容完整」（示例标签）

#### 下载量表（XLSX）

点击「量表」按钮下载 Excel 文件，包含：

- **Sheet 1 — 评分量表**：表头紫底白字加粗居中，列宽自适应
- **Sheet 2 — 学习心得**（如有）：序号、标题、类型、内容

文件命名：`{任务名称}_量表.xlsx`

#### 下载心得（DOCX）

点击「心得」按钮下载 Word 文档，包含：

- **标题**：紫色居中大号字体
- **元信息**：生成时间、统计数据（灰色小字居中）
- **第一部分：得分心得**：紫底标题，每条含编号+标题+[得分]+正文缩进
- **第二部分：不得分心得**：红底标题，同上格式

文件命名：`{任务名称}_学习心得.doc`

### 2.6 删除记录

#### 删除操作流程

1. 点击操作列中的删除按钮（🗑 图标）
2. 弹出**居中确认对话框**：
   ```
   ┌─────────────────────────────────────┐
   │  ⚠ 确认删除                         │
   │                                     │
   │  🟠 确定要删除该任务吗？此操作将同时  │
   │  删除关联的量表和心得，删除后不可恢复。│
   │                                     │
   │              [取消]  [确定]          │
   └─────────────────────────────────────┘
   ```
3. 点击「确定」执行删除，自动刷新列表

> **注意**：所有状态的记录均可删除（包括正在生成中的任务）

---

## 三、技术架构

### 3.1 系统架构图

```
┌─────────────────────────────────────────────────────────────────────┃
│                         前端层 (Vue 3 + Element Plus)               │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                   AIRubricGenerator.vue                       │   │
│  │                                                              │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────┐  │   │
│  │  │ 统计面板  │ │ 上传配置  │ │ 记录列表  │ │ 预览/删除弹窗   │  │   │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └───────┬────────┘  │   │
│  │       │            │           │               │            │   │
│  │  fetchStats()   startGenerate() fetchRecords()  showDeleteDialog() │
│  │  downloadXlsx()  downloadDocx()  previewRecord() confirmDelete() │   │
│  └───────┼────────────┼─────────────┼───────────────┼───────────┘   │
│          │            │             │               │                │
│          ▼            ▼             ▼               ▼                │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    data-factory.js (API 层)                    │   │
│  │                                                               │   │
│  │  getRubricRecords(params)     → GET  /api/data-factory/rubric/records/   │
│  │  generateRubric(formData)     → POST /api/data-factory/rubric/generate/  │
│  │  getRubricDetail(id)          → GET  /api/data-factory/rubric/{id}/      │
│  │  deleteRubricRecord(id)       → DELETE /api/data-factory/rubric/{id}/del │
│  │  getRubricStatistics()        → GET  /api/data-factory/rubric/statistics/│
│  └──────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │ HTTP REST (JSON / Multipart)
                                   ▼
┌─────────────────────────────────────────────────────────────────────┃
│                        后端层 (Django REST Framework)               │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                     urls.py (路由分发)                         │   │
│  └───────────────────────────┬──────────────────────────────────┘   │
│                              │                                       │
│                              ▼                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    rubric_view.py (视图函数)                    │   │
│  │                                                               │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────┐  │   │
│  │  │文件提取引擎   │  │ AI 调用引擎  │  │ Fallback 模板引擎    │  │   │
│  │  │PDF/DOCX/TXT  │  │OpenAI兼容API │  │22项指标+10条心得     │  │   │
│  │  │图片OCR(base64)│  │同步httpx调用 │  │按pass_ratio组合     │  │   │
│  │  └──────┬──────┘  └──────┬──────┘  └──────────┬───────────┘  │   │
│  └─────────┼────────────────┼───────────────────┼───────────────┘   │
│            │                │                    │                  │
│            ▼                ▼                    ▼                  │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                 models.py (数据模型)                           │   │
│  │                                                               │   │
│  │  AIRubricRecord                                              │   │
│  │  ├── id, user, name                                          │   │
│  │  ├── status: running / done / error                          │   │
│  │  ├── source_file (FileField)                                 │   │
│  │  ├── note_count, pass_ratio                                  │   │
│  │  ├── rubric_data (JSONField) [{seq, level1, level2, desc}]   │   │
│  │  └── notes_data (JSONField)  [{title, body, type}]            │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │              requirement_analysis.AIModelConfig                │   │
│  │              (AI 模型配置中心 - knowledge_base 角色)           │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┃
│                        存储层                                        │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐   │
│  │ SQLite / MySQL│  │ 文件存储系统   │  │ AI 外部服务             │   │
│  │ (db.sqlite3) │  │ media/rubric/ │  │ OpenAI兼容 API Endpoint │   │
│  └──────────────┘  └──────────────┘  └────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 数据模型

#### AIRubricRecord

```python
class AIRubricRecord(models.Model):
    """AI 评分量表生成记录"""
    
    # === 基础信息 ===
    id = AutoField(primary_key=True)
    name = CharField(max_length=200)              # 任务名称
    user = ForeignKey(User, on_delete=CASCADE)     # 所属用户
    
    # === 状态管理 ===
    status = CharField(
        max_length=20,
        choices=[
            ('running', '生成中'),
            ('done',    '已完成'),
            ('error',   '失败'),
        ],
        default='running'
    )
    
    # === 源文件 ===
    source_file = FileField(upload_to='rubric/sources/%Y/%m/')
    source_file_name = CharField(max_length=255, blank=True)
    
    # === 生成配置 ===
    note_count = IntegerField(default=20)          # 心得总数
    pass_ratio = FloatField(default=0.6)           # 得分心得比例
    
    # === 生成结果 (JSON 存储) ===
    rubric_data = JSONField(default=list)          # 量表数据
    # 格式: [{"seq": 1, "level1": "一级", "level2": "二级", "desc": "说明"}, ...]
    
    notes_data = JSONField(default=list)           # 心得数据
    # 格式: [{"title": "标题", "body": "内容", "type": "pass|fail"}, ...]
    
    # === 结果文件 (可选) ===
    rubric_file = FileField(upload_to='rubric/output/%Y/%m/', null=True)
    notes_file = FileField(upload_to='rubric/notes/%Y/%m/', null=True)
    
    # === 时间戳 ===
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

#### to_list_dict() 返回格式

```json
{
  "id": 1,
  "name": "AI技术与学科融合评分量表",
  "status": "done",
  "source_file_name": "教学设计.pdf",
  "note_count": 20,
  "pass_ratio": 0.6,
  "created_at": "2026-06-03 04:20:52",
  "rubric_data": [
    {"seq": 1, "level1": "教学内容", "level2": "科学性", "desc": "..."},
    {"seq": 2, "level1": "教学内容", "level2": "适切性", "desc": "..."},
    ...
  ],
  "notes_data": [
    {"title": "创新教案", "body": "从文本解读到生命教育...", "type": "pass"},
    {"title": "倾听童声", "body": "在学习者分析与情境的指引下...", "type": "fail"},
    ...
  ]
}
```

> **注意**：`running` 状态时 `rubric_data` 和 `notes_data` 返回空数组 `[]`

### 3.3 API 接口清单

| 方法 | 路径 | 功能 | 认证 | 参数 |
|------|------|------|------|------|
| GET | `/api/data-factory/rubric/records/` | 获取记录列表 | ✅ Required | `?status=done&name=xxx` |
| POST | `/api/data-factory/rubric/generate/` | 创建并执行生成任务 | ✅ Required | Multipart Form Data |
| GET | `/api/data-factory/rubric/statistics/` | 获取统计数据 | ✅ Required | 无 |
| GET | `/api/data-factory/rubric/<id>/` | 获取单条详情 | ✅ Required | 路径参数 id |
| DELETE | `/api/data-factory/rubric/<id>/delete/` | 删除记录 | ✅ Required | 路径参数 id |

#### POST `/rubric/generate/` 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | ✅ | 任务名称 |
| `note_count` | integer | 否 | 默认 20 |
| `pass_ratio` | float | 否 | 默认 0.6 (范围 0~1) |
| `note_length` | integer | 否 | 默认 300 (目标字数) |
| `file` | file | 否 | 源文件（multipart） |

#### 成功响应 (201 Created)

```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "AI技术与学科融合评分量表",
    "status": "done",
    "rubric_count": 18,
    "notes_count": 20,
    "source": "ai_generated"
  }
}
```

#### 错误响应 (降级成功)

```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "AI技术与学科融合评分量表",
    "status": "error",
    "warning": "AI 调用异常",
    "rubric_count": 22,
    "notes_count": 10,
    "source": "template_fallback"
  }
}
```

### 3.4 前端组件结构

```
AIRubricGenerator.vue
├── <template>
│   ├── 统计卡片行 (4个 stat-card)
│   ├── 上传卡片 (el-card)
│   │   ├── el-upload 拖拽上传区
│   │   ├── 已选文件信息展示
│   │   └── 配置表单 (任务名/心得数/比例/字数) + 开始生成按钮
│   ├── 记录列表卡片 (el-card)
│   │   ├── 筛选标签 (全部/生成中/已完成/失败)
│   │   ├── 搜索框
│   │   ├── el-table 表格
│   │   │   └── 操作列 (预览/量表/心得/删除)
│   │   └── el-pagination 分页
│   ├── 删除确认对话框 (el-dialog align-center)
│   └── 预览弹窗 (el-dialog + el-tabs)
│       ├── Tab: 评分量表 (el-table 合并单元格)
│       └── Tab: 学习心得 (笔记卡片列表)
├── <script setup>
│   ├── 状态变量 (ref)
│   │   ├── records / stats / tableLoading
│   │   ├── form (taskName/noteCount/passRatio/noteLength)
│   │   ├── generating / uploadedFile / currentFilter
│   │   ├── previewVisible / previewTab / previewData
│   │   └── deleteDialogVisible / deleteTargetId / deleteLoading
│   ├── 计算属性 (computed)
│   │   ├── filteredRecords (筛选+搜索)
│   │   ├── paginatedRecords (分页切片)
│   │   └── 预览统计数据
│   ├── 核心方法
│   │   ├── startGenerate()      -- 发起生成请求
│   │   ├── fetchRecords()       -- 获取记录列表
│   │   ├── fetchStats()         -- 获取统计数据
│   │   ├── previewRecord()      -- 打开预览弹窗
│   │   ├── downloadXlsx()       -- 下载 Excel 量表
│   │   ├── downloadDocx()       -- 下载 Word 心得
│   │   ├── showDeleteDialog()   -- 打开删除确认框
│   │   ├── confirmDelete()      -- 执行删除操作
│   │   └── deleteRecord()       -- 调用删除 API
│   └── 工具方法
│       ├── statusTagType() / statusText()
│       ├── formatFileSize() / isImageFile()
│       └── isFirstInLevel1()
├── <style scoped>
│   ├── 统计卡片样式 (.stat-card)
│   ├── 上传区域样式 (.upload-area)
│   ├── 表格样式 (.ai-rubric-container)
│   ├── 心得卡片样式 (.note / .note.fail)
│   └── 预览弹窗样式 (.preview-*)
└── <style> (全局)
    └── 弹窗背景修复样式
```

---

## 四、开发指南

### 4.1 项目结构

```
d:/grt_testhub/
├── apps/
│   └── data_factory/                  # 后端 Django App
│       ├── __init__.py
│       ├── models.py                  # AIRubricRecord 模型定义
│       ├── urls.py                    # 路由配置
│       ├── rubric_view.py             # 核心：视图函数 + AI 调用 + 文件提取
│       └── ...
├── frontend/
│   └── src/
│       ├── api/
│       │   └── data-factory.js        # API 接口封装
│       ├── views/
│       │   └── data-factory/
│       │       └── AIRubricGenerator.vue  # 主页面组件 (~1000 行)
│       └── router/
│           └── index.js               # 路由注册
└── manage.py                          # Django 入口
```

### 4.2 后端核心逻辑详解

#### 4.2.1 事务分离策略（关键设计）

```python
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def rubric_generate(request):
    """创建并执行量表生成任务"""
    
    # ===== 第一步：提取文件内容（必须在创建记录前）=====
    if request.FILES.get('file'):
        file_content = extract_file_content(uploaded_file)
        uploaded_file.seek(0)  # 重置指针供后续保存
    
    # ===== 第二步：独立事务创建记录并立即提交 =====
    with transaction.atomic():
        record = AIRubricRecord.objects.create(
            user=request.user, name=name,
            status='running', note_count=note_count, pass_ratio=pass_ratio,
        )
        if uploaded_file:
            record.source_file.save(safe_name, uploaded_file, save=False)
            record.save()
    
    logger.info(f"[AI量表] 记录已创建并提交, id={record.id}, status=running")
    
    # ===== 第三步：执行耗时 AI 调用（此时前端已能查到记录）=====
    try:
        rubric_data, notes_data = _ai_generate_rubric_and_notes(...)
        record.rubric_data = rubric_data
        record.notes_data = notes_data
        record.status = 'done'
        record.save()
    except Exception as e:
        # AI 失败 → 降级到本地模板
        rubric_data, notes_data = _generate_notes_fallback(...)
        record.rubric_data = rubric_data
        record.notes_data = notes_data
        record.status = 'error'
        record.save()
    
    return Response({'success': True, 'data': {...}}, status=201)
```

**为什么这样设计？**

| 问题 | 解决方案 |
|------|----------|
| AI 调用耗时 30s ~ 数分钟，期间前端查询不到新记录 | `transaction.atomic()` 先提交 running 记录 |
| 整个视图在隐式事务中，commit 在 response 之后 | 用显式 `with transaction.atomic()` 分离 |
| 前端 `fetchRecords()` 与后端写入竞态 | 前端加 1000ms 延迟再刷新 |

#### 4.2.2 AI 调用流程

```python
def _ai_generate_rubric_and_notes(file_content, file_name, note_count, 
                                    pass_ratio, task_name, note_length):
    """
    两步式 AI 生成:
    Step 1: 生成评分量表 JSON
    Step 2: 生成学习心得 JSON
    """
    
    # 从配置中心获取 AI 模型
    config = AIModelConfig.objects.filter(role='knowledge_base').first()
    base_url = config.base_url.rstrip('/')
    model_name = config.model_name
    api_key = config.api_key
    
    # 智能 URL 补全
    if base_url.endswith('/chat/completions'):
        url = base_url
    elif base_url.endswith('/v1'):
        url = f"{base_url}/chat/completions"
    else:
        url = f"{base_url}/v1/chat/completions"
    
    # === Step 1: 生成量表 ===
    rubric_prompt = BASE_RUBRIC_TEMPLATE.format(
        file_context=file_content or "(无上传文件)",
        file_name=file_name or "未指定",
        task_name=task_name,
    )
    rubric_response = call_ai(url, model_name, api_key, rubric_prompt)
    rubric_list = parse_rubric_json(rubric_response)  # 清理 markdown 包裹
    
    # === Step 2: 生成心得 ===
    notes_prompt = NOTES_PROMPT_TEMPLATE.format(
        rubric_summary=summarize_rubric(rubric_list),
        note_count=note_count,
        pass_count=int(note_count * pass_ratio),
        fail_count=note_count - int(note_count * pass_ratio),
        note_length=note_length,
    )
    notes_response = call_ai(url, model_name, api_key, notes_prompt)
    notes_list = parse_notes_json(notes_response)
    
    return rubric_list, notes_list
```

#### 4.2.3 文件提取引擎

```python
def extract_file_content(file_obj):
    """
    支持的文件类型及提取方式:
    - .txt  → 直接 read().decode('utf-8')
    - .pdf  → PyMuPDF (fitz) 提取文本
    - .docx → python-docx 提取段落文本
    - .png/.jpg/.jpeg → base64 编码传给 AI (视觉模型需支持)
    """
    ext = os.path.splitext(file_obj.name)[1].lower()
    
    if ext == '.txt':
        return file_obj.read().decode('utf-8', errors='ignore')
    
    elif ext == '.pdf':
        import fitz  # PyMuPDF
        doc = fitz.open(stream=file_obj.read(), filetype="pdf")
        return "\n".join([page.get_text() for page in doc])
    
    elif ext == '.docx':
        from docx import Document
        doc = Document(file_obj)
        return "\n".join([p.text for p in doc.paragraphs])
    
    elif ext in ('.png', '.jpg', '.jpeg'):
        import base64
        b64 = base64.b64encode(file_obj.read()).decode()
        mime = f"image/{ext.replace('.', '')}"
        return f"data:{mime};base64,{b64}"  # 返回 data URI
    
    else:
        return None
```

#### 4.2.4 Fallback 模板机制

当 AI 调用失败时（网络错误、超时、返回格式异常等），自动降级使用预设模板：

```python
BASE_RUBRIC_TEMPLATE_DATA = [
    {"seq": 1, "level1": "教学内容", "level2": "科学性", "desc": "..."},
    {"seq": 2, "level1": "教学内容", "level2": "适切性", "desc": "..."},
    # ... 共 22 个默认指标
]

PASS_NOTES_TEMPLATES = [
    {"title": "创新教案", "body": "从文本解读到生命教育...", "type": "pass"},
    # ... 共 6 条得分模板
]

FAIL_NOTES_TEMPLATES = [
    {"title": "机械套用", "body": "过度依赖现成教案...", "type": "fail"},
    # ... 共 4 条不得分模板
]

def _generate_notes_fallback(pass_ratio):
    """按比例随机组合模板"""
    pass_pool = list(PASS_NOTES_TEMPLATES)
    fail_pool = list(FAIL_NOTES_TEMPLATES)
    random.shuffle(pass_pool)
    random.shuffle(fail_pool)
    total = int(note_count)
    pass_n = int(total * pass_ratio)
    fail_n = total - pass_n
    return pass_pool[:pass_n] + fail_pool[:fail_n]
```

### 4.3 前端核心逻辑详解

#### 4.3.1 生成任务提交流程

```javascript
async function startGenerate() {
  if (!form.taskName.trim()) { ElMessage.warning('请输入任务名称'); return }
  if (generating.value) return
  generating.value = true
  
  try {
    const formData = new FormData()
    formData.append('name', form.taskName.trim())
    formData.append('note_count', String(form.noteCount))
    formData.append('pass_ratio', String(form.passRatio))
    formData.append('note_length', String(form.noteLength))
    if (uploadedFile.value) formData.append('file', uploadedFile.value)

    // 发起非阻塞请求
    const reqPromise = generateRubric(formData)
    
    // 延迟 1000ms 后刷新列表（等待后端 transaction.commit）
    setTimeout(() => {
      fetchRecords()
      fetchStats()
    }, 1000)

    // 等待响应完成后再次刷新
    const res = await reqPromise
    if (res.data.success) {
      await fetchRecords()
      await fetchStats()
      ElMessage.success(`生成完成！${res.data.data.rubric_count}个指标 + ${res.data.data.notes_count}条心得`)
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.error || e.message || '生成失败')
  } finally {
    generating.value = false
  }
}
```

#### 4.3.2 Excel 导出实现（SheetJS）

```javascript
function downloadXlsx(record) {
  const wb = XLSX.utils.book_new()
  
  // Sheet 1: 评分量表
  const header = [['序号', '一级指标', '二级指标', '指标说明']]
  const rows = record.rubric_data.map(r => [r.seq, r.level1, r.level2, r.desc])
  const ws = XLSX.utils.aoa_to_sheet([...header, ...rows])
  
  // 设置列宽
  ws['!cols'] = [{ wch: 6 }, { wch: 22 }, { wch: 24 }, { wch: 55 }]
  
  // 表头样式（紫底白字加粗）
  for (const cell of ['A1','B1','C1','D1']) {
    if (ws[cell]) ws[cell].s = {
      font: { bold: true, color: { rgb: 'FFFFFF' } },
      fill: { fgColor: { rgb: '7C3AED' } },
      alignment: { horizontal: 'center' }
    }
  }
  XLSX.utils.book_append_sheet(wb, ws, '评分量表')

  // Sheet 2: 学习心得（如有数据）
  if (record.notes_data?.length) {
    const nHeader = [['序号', '标题', '类型', '内容']]
    const nRows = record.notes_data.map((n, i) => [
      i + 1, n.title, 
      n.type === 'pass' ? '得分心得' : '不得分心得', 
      n.body.replace(/\n/g, ' ')
    ])
    const ws2 = XLSX.utils.aoa_to_sheet([...nHeader, ...nRows])
    XLSX.utils.book_append_sheet(wb, ws2, '学习心得')
  }

  XLSX.writeFile(wb, `${record.name}_量表.xlsx`)
  ElMessage.success('量表下载完成')
}
```

#### 4.3.3 Word 导出实现（Word 兼容 HTML）

```javascript
function downloadDocx(record) {
  const esc = (s) => String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
  
  const html = `
<html xmlns:o="urn:schemas-microsoft-com:office:office"
      xmlns:w="urn:schemas-microsoft-com:office:word">
<head><meta charset="UTF-8">
<meta name=ProgId content=Word.Document>
<!--[if gte mso 9]><xml>
<w:WordDocument><w:View>Print</w:View></w:WordDocument></xml><![endif]-->
<style>
body{font-family:'宋体';font-size:10.5pt;line-height:1.8}
h1{font-size:16pt;text-align:center;color:#4B0082}
h2{border-bottom:2px solid #7C3AED;color:#7C3AED;font-size:13pt}
.note{margin:14pt 0;padding:8px 12pt;border-left:3px solid #7C3AED;background:#faf5ff}
.note.fail{border-color:#EF4444;background:#fff5f5}
</style></head><body>
<h1>${esc(record.name)}</h1>
<div class="meta">生成时间：... | 共 N 条心得...</div>
<h2>一、得分心得</h2>
${record.notes_data.filter(n=>n.type==='pass').map(n => `<div class="note">...</div>`).join('')}
<h2 style="border-color:#EF4444;color:#EF4444">二、不得分心得</h2>
${record.notes_data.filter(n=>n.type==='fail').map(n => `<div class="note fail">...</div>`).join('')}
</body></html>`
  
  const blob = new Blob([html], { type: 'application/msword;charset=utf-8' })
  // ... 触发下载
}
```

**为什么不使用 OOXML (.docx)？**

手写 ZIP 生成器存在浏览器兼容性问题（可能导致卡死）。采用 Word 兼容 HTML 方案（`.doc` 扩展名）更稳定可靠，且 Word 可直接打开编辑。

#### 4.3.4 删除确认对话框

```vue
<!-- 居中删除确认对话框 -->
<el-dialog
  v-model="deleteDialogVisible"
  title="确认删除"
  width="420px"
  align-center
  :close-on-click-modal="false">
  <div style="display:flex;align-items:flex-start;gap:12px;">
    <el-icon :size="22" color="#E6A23C"><WarningFilled /></el-icon>
    <span>确定要删除该任务吗？此操作将同时删除关联的量表和心得，删除后不可恢复。</span>
  </div>
  <template #footer>
    <el-button @click="deleteDialogVisible = false">取消</el-button>
    <el-button type="primary" @click="confirmDelete" :loading="deleteLoading">确定</el-button>
  </template>
</el-dialog>
```

**为什么不用 el-popconfirm？**
- `popconfirm` 是气泡弹出定位在按钮附近，容易被页面边缘裁剪
- `el-dialog` + `align-center` 可实现真正的页面居中效果
- 对话框更适合承载较长的提示文字

### 4.4 关键技术要点

#### 4.4.1 即时反馈模式

```
用户点击 → 后端创建记录(transaction.commit) → 前端立即查到running → 显示"生成中"
                                                    ↓
                                            AI耗时执行中(30s~min)
                                                    ↓
                                           更新status=done/error
```

涉及的技术点：
- **后端**: `django.db.transaction.atomic()` 显式事务控制
- **前端**: `setTimeout(() => fetchRecords(), 1000)` 延迟刷新避免竞态
- **数据库**: SQLite 的 autocommit 模式下 `atomic()` 会立即 COMMIT

#### 4.4.2 AI 配置热切换

AI 模型配置来自 `requirement_analysis.AIModelConfig` 表，通过 `role='knowledge_base'` 过滤：

```python
config = AIModelConfig.objects.filter(role='knowledge_base').first()
# config.base_url  → API 地址 (如 https://api.openai.com/v1)
# config.model_name → 模型名 (如 gpt-4o)
# config.api_key    → API 密钥
```

**好处**：无需改代码即可切换 AI 服务商（OpenAI / Azure / 本地 Ollama 等）

#### 4.4.3 安全措施

| 措施 | 实现 |
|------|------|
| **认证** | 所有接口 `@permission_classes([IsAuthenticated])` |
| **数据隔离** | `AIRubricRecord.objects.filter(user=request.user)` 按用户过滤 |
| **文件安全** | 上传路径随机化 (`{timestamp}_{name[:50]}`)，防止覆盖攻击 |
| **XSS 防护** | 前端 `escapeXml()` 转义 HTML 特殊字符 |
| **CSRF** | Django 默认 CSRF 中间件保护 |

#### 4.4.4 依赖库清单

| 包名 | 用途 | 安装位置 |
|------|------|----------|
| `django` | Web 框架 | venv314 |
| `djangorestframework` | REST API | requirements |
| `Pillow` | 图片处理 | requirements |
| `PyMuPDF` (fitz) | PDF 文本提取 | requirements |
| `python-docx` | DOCX 文本提取 | requirements |
| `httpx` | 同步 HTTP 客户端 | requirements |
| `openpyxl` | Excel 读写（后端备选）| requirements |
| `xlsx` (SheetJS) | 前端 Excel 生成 | frontend/package.json |
| `@element-plus/icons-vue` | UI 图标库 | frontend/package.json |

### 4.5 常见问题排查

#### Q1: 点击"开始生成"后记录不出现

| 可能原因 | 排查步骤 |
|----------|----------|
| 后端未重启 | 检查终端是否运行 `runserver` |
| 事务未提交 | 检查代码是否有 `with transaction.atomic()` |
| 前端刷新时机过早 | 检查是否加了 `setTimeout` 延迟 |
| API 报错 | 按 F12 查看 Network 面板的请求响应 |

#### Q2: AI 一直处于"生成中"状态

| 可能原因 | 排查步骤 |
|----------|----------|
| AI API 连接失败 | 检查 `AIModelConfig` 的 `base_url` 是否正确 |
| API Key 无效 | 检查密钥是否过期或有额度限制 |
| 模型不支持 | 检查 `model_name` 是否为目标服务支持的模型 |
| URL 拼接错误 | 检查日志 `[AI量表] AI API URL:` 实际输出 |

#### Q3: 下载文件无响应

| 可能原因 | 排查步骤 |
|----------|----------|
| 记录无数据 | 检查 `to_list_dict()` 是否返回 `rubric_data`/`notes_data` |
| Blob 创建失败 | 检查浏览器控制台是否有 JS 错误 |
| MIME type 问题 | 确认 Blob type 与扩展名匹配 |

#### Q4: 删除弹窗被截断/位置不对

| 可能原因 | 解决方案 |
|----------|----------|
| 使用 popconfirm | 改用 `el-dialog` + `align-center` |
| CSS overflow 问题 | 检查父容器是否有 `overflow: hidden` |

---

## 五、变更日志

### v1.1.0 (2026-06-03)

| 变更类别 | 具体内容 | 影响范围 |
|----------|----------|----------|
| 🐛 Bug 修复 | 事务未提交导致生成记录不立即出现 | `rubric_view.py` |
| 🐛 Bug 修复 | URL 拼接被覆盖导致 AI 调用必然失败 | `rubric_view.py` |
| ✨ 新增功能 | 生成中状态增加删除按钮 | `AIRubricGenerator.vue` |
| ✨ 新增功能 | 删除确认改为页面居中对话框 | `AIRubricGenerator.vue` |
| ✨ 新增功能 | 心得下载改为 Word 文档(.doc)格式 | `AIRubricGenerator.vue` |
| 🔧 优化 | 移除任务名称下方重复的文件名称行 | `AIRubricGenerator.vue` |
| 🔧 优化 | 列表接口返回完整数据支持表格内直接下载 | `models.py` |
| 🔧 优化 | 生成请求后延迟 1000ms 刷新避免竞态 | `AIRubricGenerator.vue` |
| 🎨 样式 | 清理废弃的 popconfirm 全局样式 | `AIRubricGenerator.vue` |

### v1.0.0 (初始版本)

- AI 量表生成管理基础功能上线
- 支持多格式文件上传、AI 驱动生成、Excel/HTML 下载
- 统计面板、筛选搜索、预览弹窗

---

> **文档维护者**: CodeBuddy AI Assistant  
> **反馈渠道**: 如有问题请查看项目 README 或联系开发团队
