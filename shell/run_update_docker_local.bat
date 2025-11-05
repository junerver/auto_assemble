:: 该脚本用于推送镜像到本地的 docker 容器

@echo off
:: 设置代码页为 UTF-8（如果需要支持 UTF-8 编码）
chcp 65001 >nul
setlocal enabledelayedexpansion

:: 获取脚本所在目录和项目根目录
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..

:: 切换到项目根目录，确保所有操作都在正确位置执行
cd /d "%PROJECT_ROOT%"

:: 显示当前工作目录用于调试
echo Current working directory: %CD%

:: 检查Docker是否运行
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo Docker未运行，请先启动Docker
    exit /b 1
)

:: 检查私有仓库是否可访问
ping -n 1 192.168.172.110 >nul 2>&1
if %errorlevel% neq 0 (
    echo 无法连接到Docker私有仓库 192.168.172.110
    exit /b 1
)

:: 构建Docker镜像
echo 开始构建Docker镜像...
docker build -t auto_assemble-webhook:fast_api -f docker/Dockerfile .
if %errorlevel% neq 0 (
    echo Docker镜像构建失败
    exit /b 1
)

:: 标记镜像
echo 标记镜像...
docker tag auto_assemble-webhook:fast_api 192.168.172.110:5000/auto_assemble-webhook:fast_api
if %errorlevel% neq 0 (
    echo 镜像标记失败
    exit /b 1
)

:: 推送镜像
echo 推送镜像到私有仓库...
docker push 192.168.172.110:5000/auto_assemble-webhook:fast_api
if %errorlevel% neq 0 (
    echo 镜像推送失败
    exit /b 1
)

:: 在项目根目录下更新镜像
echo Start updating containers...
docker-compose -f docker/docker-compose.yml down
docker-compose -f docker/docker-compose.yml up -d

echo 更新完成！
exit /b 0

