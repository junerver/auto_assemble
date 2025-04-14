import os
from pathlib import Path

# 数据库配置
DB_FILE = Path(__file__).parent / "webhook_server.db"

# 服务器配置
PORT = int(os.getenv("PORT", 5005))
DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"

# 任务配置
CHECK_INTERVAL = 1  # 检查间隔（秒）
TASK_TIMEOUT = 600  # 任务超时时间（秒）
MAX_RETRIES = 3  # 最大重试次数
