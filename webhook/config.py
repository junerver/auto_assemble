import os
from pathlib import Path

from dotenv import load_dotenv

# 加载环境变量
env_path = Path(os.path.dirname(os.path.abspath(__file__))) / ".env"
if not env_path.exists():
    print(f"环境变量文件 '{env_path}' 不存在")
else:
    load_dotenv(env_path)
    print(f"已加载环境变量文件: {env_path}")

# 数据库配置
DB_FILE = Path(__file__).parent / "webhook_server.db"

# 服务器配置
PORT = int(os.getenv("PORT", 5005))
DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"

# 任务配置
CHECK_INTERVAL = 1  # 检查间隔（秒）
TASK_TIMEOUT = 600  # 任务超时时间（秒）
MAX_RETRIES = 3  # 最大重试次数
