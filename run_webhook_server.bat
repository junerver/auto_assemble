@echo off
setlocal

:: 调用公共配置
call config.bat

cd /d %MODULE_DIR%
:: 激活 venv
call venv\Scripts\activate.bat

:: 使用当前激活环境中的 Python 运行 push 脚本
uv run webhook

pause
