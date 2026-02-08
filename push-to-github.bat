@echo off
chcp 65001
echo ==========================================
echo 推送代码到 GitHub
echo ==========================================
echo.

cd /d D:\testhub\grt_testhub

echo [1/3] 检查远程仓库...
git remote -v

echo.
echo [2/3] 推送代码到远程仓库...
git push -u origin master

echo.
if %errorlevel% == 0 (
    echo ==========================================
    echo 推送成功！
    echo ==========================================
) else (
    echo ==========================================
    echo 推送失败，请检查：
    echo 1. 网络连接是否正常
    echo 2. GitHub 用户名和密码/Token 是否正确
    echo 3. 是否有仓库的写入权限
    echo ==========================================
)

pause
