"""
Configuration Module

This module provides configuration management for the manager client.
"""

import os

from dotenv import load_dotenv

# 加载环境变量
env_path = os.path.join(os.getcwd(), ".env")
print(f"加载文件路径：{env_path}")
if os.path.exists(env_path):
    load_dotenv(env_path)

# 配置项
SERVER_HOST_URL = os.getenv("SERVER_HOST_URL", "http://localhost:5005")
RECONNECT_INTERVAL = int(os.getenv("RECONNECT_INTERVAL", "5"))
