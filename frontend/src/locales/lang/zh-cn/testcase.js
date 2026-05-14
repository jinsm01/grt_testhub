export default {
  testcase: {
    // Page titles
    title: '测试用例',
    detail: '用例详情',
    edit: '编辑测试用例',
    create: '创建测试用例',

    // Form sections
    basicInfo: '基本信息',
    properties: '基本信息',
    testContent: '测试内容',

    // Actions
    newCase: '新建用例',
    batchDelete: '批量删除',
    exportExcel: '导出Excel',
    saveChanges: '保存修改',
    createCase: '创建用例',
    delete: '删除用例',

    // Field labels
    caseTitle: '用例名称',
    caseDescription: '用例描述',
    project: '归属目录',
    relatedProject: '归属目录',
    relatedVersions: '关联版本',
    moduleLabel: '模块',
    priority: '用例级别',
    status: '状态',
    testType: '步骤模式',
    preconditions: '前置条件',
    steps: '测试步骤',
    expectedResult: '预期结果',
    author: '创建者',
    createdAt: '创建时间',
    creator: '创建者',
    createTime: '创建时间',
    serialNumber: '序号',

    // Priority
    low: '低',
    medium: '中',
    high: '高',
    critical: '紧急',

    // Status
    draft: '草稿',
    active: '启用',
    deprecated: '废弃',

    // Step modes
    text: '文本模式',
    step: '步骤模式',

    // Review status
    reviewStatus: '审核结果',
    reviewComment: '审核意见',
    reviewer: '审核人',
    reviewPending: '待审核',
    reviewApproved: '已通过',
    reviewRejected: '已拒绝',
    reviewNone: '未审核',

    // Placeholders
    searchPlaceholder: '搜索用例名称',
    caseTitlePlaceholder: '请输入测试用例标题',
    caseDescriptionPlaceholder: '请输入用例描述',
    selectProject: '请选择项目',
    categoryPathPlaceholder: '格式：端名称/菜单/子菜单',
    modulePlaceholder: '请输入模块名称',
    selectPriority: '请选择优先级',
    selectTestType: '请选择测试类型',
    selectStatus: '请选择状态',
    selectVersions: '请选择版本（可多选）',
    preconditionsPlaceholder: '请输入前置条件',
    stepsPlaceholder: '请输入详细的操作步骤，如：\n1. 打开登录页面\n2. 输入用户名和密码\n3. 点击登录按钮\n4. 验证登录结果',
    expectedResultPlaceholder: '请输入整体预期结果',
    priorityFilter: '用例级别',
    moduleFilter: '模块筛选',
    statusFilter: '状态筛选',

    // Messages
    fetchListFailed: '获取测试用例列表失败',
    fetchDetailFailed: '获取用例详情失败',
    deleteConfirm: '确定要删除这个测试用例吗？',
    deleteSuccess: '测试用例删除成功',
    deleteFailed: '测试用例删除失败',
    selectFirst: '请先选择要删除的测试用例',
    batchDeleteConfirm: '确定要删除选中的 {count} 个测试用例吗？此操作不可恢复。',
    batchDeleteSuccess: '成功删除 {successCount} 个测试用例',
    batchDeletePartialSuccess: '成功删除 {successCount} 个测试用例，{failCount} 个失败',
    batchDeleteFailed: '删除失败',
    batchDeleteError: '批量删除失败',
    noDataToExport: '没有测试用例数据可导出',
    exportSuccess: '测试用例导出成功',
    exportFailed: '导出测试用例失败',
    createSuccess: '测试用例创建成功',
    createFailed: '测试用例创建失败',
    updateSuccess: '测试用例修改成功',
    updateFailed: '测试用例修改失败',
    fetchProjectsFailed: '获取项目列表失败',
    fetchVersionsFailed: '获取项目版本失败',

    // Other
    noVersion: '未关联版本',
    noProject: '未关联项目',
    noDescription: '暂无描述',
    none: '无',
    baseline: '基线',

    // Validation
    titleRequired: '请输入用例标题',
    titleLength: '标题长度在 5 到 500 个字符',
    expectedResultRequired: '请输入预期结果',
    stepsMaxLength: '操作步骤不能超过1000个字符',

    // Excel export
    excelNumber: '测试用例编号',
    excelTitle: '用例标题',
    excelProject: '关联项目',
    excelVersions: '关联版本',
    excelPreconditions: '前置条件',
    excelSteps: '操作步骤',
    excelExpectedResult: '预期结果',
    excelPriority: '优先级',
    excelStatus: '状态',
    excelTestType: '测试类型',
    excelAuthor: '作者',
    excelCreatedAt: '创建时间',
    excelSheetName: '测试用例',
    excelFileName: '测试用例_{date}.xlsx',

    // Import
    import: '导入',
    export: '导出',
    importTitle: '导入测试用例',
    dragFile: '将文件拖到此处，或',
    clickUpload: '点击上传',
    uploadTip: '支持 .xlsx, .xls 格式文件，文件大小不超过 10MB',
    fieldMapping: '字段映射配置',
    excelField: 'Excel字段',
    systemField: '系统字段',
    selectField: '选择映射字段',
    dataPreview: '数据预览',
    records: '条记录',
    confirmImport: '确认导入',
    parseSuccess: '成功解析 {count} 条数据',
    parseFailed: '解析Excel文件失败',
    emptyExcel: 'Excel文件为空或格式不正确',
    readFileFailed: '读取文件失败',
    noTitleMapping: '请至少映射用例标题字段',
    rowNoTitle: '第 {row} 行缺少用例标题',
    rowImportFailed: '第 {row} 行导入失败: {error}',
    importAllSuccess: '成功导入 {count} 条测试用例',
    importPartialMessage: '导入完成，成功 {success} 条，失败 {fail} 条',
    importSuccess: '导入成功',
    importPartialSuccess: '部分导入成功',
    importFailed: '导入失败',
    importResult: '导入结果',
    importSuccessCount: '成功',
    importFailCount: '失败',
    errorDetails: '错误详情',
    categoryLabel: '归属目录'
  },
  testSuite: {
    title: '测试套件',
    newSuite: '新建套件',
    inDevelopment: '测试套件功能开发中...'
  }
}
