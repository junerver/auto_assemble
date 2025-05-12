@REM 用于从实际的打包服务器同步数据库到本地

@echo off
:: 设置代码页为 UTF-8（如果需要支持 UTF-8 编码）
chcp 65001 >nul

:: 设置远程服务器信息
set REMOTE_USER=root
set REMOTE_HOST=192.168.189.243
set REMOTE_FILE=/opt/auto_assemble/webhook/webhook_server.db

:: 设置本地目标目录
set LOCAL_DIR=E:/dev/auto_assemble/webhook/
set LOCAL_FILE=%LOCAL_DIR%webhook_server.db

:: 检查本地目标目录是否存在
if not exist "%LOCAL_DIR%" (
    echo 错误：本地目录 "%LOCAL_DIR%" 不存在，请先创建该目录。
    exit /b 1
)

:: 提示用户正在执行操作
echo 正在从远程服务器下载文件...
echo 远程文件路径：%REMOTE_FILE%
echo 本地目标路径：%LOCAL_FILE%

:: 使用 scp 命令下载文件，并忽略警告信息
scp -o StrictHostKeyChecking=no %REMOTE_USER%@%REMOTE_HOST%:%REMOTE_FILE% "%LOCAL_FILE%" >nul 2>&1

:: 检查 scp 命令是否成功
if %errorlevel% neq 0 (
    echo 错误：文件下载失败，请检查网络连接或服务器配置。
    exit /b 1
)

:: 提示下载成功
echo 文件已成功下载并覆盖到本地目录。

pause