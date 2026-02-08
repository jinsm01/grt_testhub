@echo off
chcp 65001
echo ==========================================
echo Git 提交脚本
echo ==========================================
echo.

cd /d D:\testhub\grt_testhub

echo [1/6] 检查 Git 状态...
git status
if errorlevel 1 (
    echo [1/6] 初始化 Git 仓库...
    git init
)

echo.
echo [2/6] 添加远程仓库...
git remote remove origin 2>nul
git remote add origin https://github.com/jinsm01/grt_testhub.git

echo.
echo [3/6] 添加所有文件...
git add .

echo.
echo [4/6] 提交更改...
git commit -m "优化前端页面样式

- 优化 ReviewDetail.vue 样式，参考 ReviewList.vue 设计风格
- 优化 ReviewForm.vue 页面样式，统一紫色主题
- 修复 TestCaseEdit.vue 表单项间距问题
- 修复 ReviewForm.vue 对话框按钮样式
- 修复 ReviewTemplateList.vue 对话框按钮样式和表单间距
- 统一对话框样式，使用 dialog-footer class"

echo.
echo [5/6] 推送到远程仓库...
git push -u origin master

echo.
echo ==========================================
echo 提交完成！
echo ==========================================
pause
