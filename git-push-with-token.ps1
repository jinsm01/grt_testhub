# Git 推送脚本 - 使用个人访问令牌
# 请替换 YOUR_GITHUB_TOKEN 为你的 GitHub 个人访问令牌

$token = Read-Host -Prompt "请输入你的 GitHub 个人访问令牌" -AsSecureString
$tokenPlain = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto([System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($token))

$repoUrl = "https://$tokenPlain@github.com/jinsm01/grt_testhub.git"

cd D:\testhub\grt_testhub

Write-Host "配置远程仓库..."
& 'C:\Program Files\Git\bin\git.exe' remote remove origin 2>$null
& 'C:\Program Files\Git\bin\git.exe' remote add origin $repoUrl

Write-Host "推送到 GitHub..."
& 'C:\Program Files\Git\bin\git.exe' push -u origin master

Write-Host "清理..."
& 'C:\Program Files\Git\bin\git.exe' remote remove origin 2>$null
& 'C:\Program Files\Git\bin\git.exe' remote add origin https://github.com/jinsm01/grt_testhub.git

Write-Host "完成！"
pause
