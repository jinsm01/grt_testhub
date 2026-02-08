# Git 提交和推送脚本
Set-Location -Path "D:\testhub\grt_testhub"

# 检查 Git 是否初始化
if (-not (Test-Path -Path ".git")) {
    Write-Host "初始化 Git 仓库..."
    git init
}

# 添加远程仓库
git remote remove origin 2>$null
git remote add origin https://github.com/jinsm01/grt_testhub.git

# 检查是否有文件需要提交
$status = git status --porcelain
if ($status) {
    Write-Host "添加所有文件..."
    git add .
    
    Write-Host "提交更改..."
    git commit -m "优化前端页面样式

- 优化 ReviewDetail.vue 样式，参考 ReviewList.vue 设计风格
- 优化 ReviewForm.vue 页面样式，统一紫色主题
- 修复 TestCaseEdit.vue 表单项间距问题
- 修复 ReviewForm.vue 对话框按钮样式
- 修复 ReviewTemplateList.vue 对话框按钮样式和表单间距
- 统一对话框样式，使用 dialog-footer class"
    
    Write-Host "推送到远程仓库..."
    git push -u origin master
    
    Write-Host "完成！"
} else {
    Write-Host "没有需要提交的更改"
}
