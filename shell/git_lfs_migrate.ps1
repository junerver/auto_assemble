#####################################################################
## 迁移git lfs文件 脚本
#####################################################################

# 设置目标仓库 TARGET_DIR
$TARGET_DIR = "D:\dev\identify_field\app-distribution"

# 定义要处理的分支列表
$BRANCHES = @("master", "test", "release")

# 设置错误处理
$ErrorActionPreference = "Stop"

# 切换到目标目录
Set-Location $TARGET_DIR

# 拉取同步到最新状态
Write-Host "正在同步仓库到最新状态..." -ForegroundColor Green
git fetch
git reset --hard HEAD
git clean -fd

# 遍历处理每个分支
foreach ($branch in $BRANCHES) {
    Write-Host "`n开始处理 $branch 分支..." -ForegroundColor Yellow
    
    try {
        # 切换到指定分支
        Write-Host "切换到 $branch 分支..." -ForegroundColor Cyan
        git checkout $branch
        
        # 同步到最新状态
        Write-Host "同步 $branch 分支到最新状态..." -ForegroundColor Cyan
        git pull origin $branch
        
        # 执行git lfs migrate
        Write-Host "在 $branch 分支上执行 git lfs migrate..." -ForegroundColor Cyan
        git lfs migrate import --everything --include="*.zip, *.bak, *.apk, *.exe" --verbose
        
        Write-Host "$branch 分支处理完成" -ForegroundColor Green
    }
    catch {
        Write-Host "处理 $branch 分支时发生错误: $_" -ForegroundColor Red
        continue
    }
}

Write-Host "`n所有分支处理完成" -ForegroundColor Green



