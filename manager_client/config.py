"""
Configuration Module

This module provides configuration management for the manager client.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# 加载环境变量
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

# 配置项
SERVER_HOST_URL = os.getenv("SERVER_HOST_URL", "http://localhost:5005")
RECONNECT_INTERVAL = int(os.getenv("RECONNECT_INTERVAL", "5"))
