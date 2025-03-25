@echo off
setlocal

:: 调用公共配置
call config.bat

cd /d %MODULE_DIR%
:: 激活 venv
call venv\Scripts\activate.bat
:: 执行完整流程
auto-assemble

pause
