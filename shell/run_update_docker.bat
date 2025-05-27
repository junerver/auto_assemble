@echo off
:: 设置代码页为 UTF-8（如果需要支持 UTF-8 编码）
chcp 65001 >nul
setlocal enabledelayedexpansion

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
docker build -t auto_assemble-webhook:fast_api -f Dockerfile .
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

:: 检查SSH连接
echo 检查SSH连接...
ssh -o BatchMode=yes -o ConnectTimeout=5 root@192.168.189.243 echo "SSH连接成功" >nul 2>&1
if %errorlevel% neq 0 (
    echo 无法通过SSH连接到服务器
    exit /b 1
)

:: 部署到服务器并清理旧镜像
echo 开始部署到服务器...
ssh root@192.168.189.243 -t "cd /opt/auto_assemble && docker-compose down && docker-compose pull && docker-compose up -d "
:: 移除旧版本 && LATEST_ID=$(docker images 192.168.172.110:5000/auto_assemble-webhook:fast_api --format '{{.ID}}') && docker images 192.168.172.110:5000/auto_assemble-webhook --format '{{.ID}}' | grep -v $LATEST_ID | xargs -r docker rmi -f
if %errorlevel% neq 0 (
    echo 服务器部署失败
    exit /b 1
)

echo 部署完成！
exit /b 0

