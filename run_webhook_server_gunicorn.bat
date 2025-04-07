@echo off
setlocal

:: 调用公共配置
call config.bat

cd /d %MODULE_DIR%
:: 激活 venv
call venv\Scripts\activate.bat


:: 启动waitress服务器
python -m waitress --port=5005 --host=0.0.0.0 webhook_server:app

pause