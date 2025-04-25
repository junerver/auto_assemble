import os
from pathlib import Path

from dotenv import load_dotenv

# 从环境变量读取配置
DISTRIBUTION_PATH = os.getenv("DISTRIBUTION_PATH")
ANDROID_UNI_BASE_PATH = os.getenv("ANDROID_UNI_BASE_PATH")
SERVER_HOST_URL = os.getenv("SERVER_HOST_URL")
PORT = int(os.getenv("PORT", 5005))
DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"

# 打印当前环境变量状态
print(
    f"当前环境变量：\nDISTRIBUTION_PATH: {DISTRIBUTION_PATH}\nANDROID_UNI_BASE_PATH: {ANDROID_UNI_BASE_PATH}\nSERVER_HOST_URL: {SERVER_HOST_URL}\nPORT: {PORT}\nDEBUG: {DEBUG}"
)

# 检查必需的环境变量
required_vars = {
    "DISTRIBUTION_PATH": DISTRIBUTION_PATH,
    "ANDROID_UNI_BASE_PATH": ANDROID_UNI_BASE_PATH,
    "SERVER_HOST_URL": SERVER_HOST_URL,
}

missing_vars = [var for var, value in required_vars.items() if value is None]
if missing_vars:
    env_path = Path(os.path.dirname(os.path.abspath(__file__))) / ".env"
    if not env_path.exists():
        print(f"环境变量文件 '{env_path}' 不存在")
    else:
        load_dotenv(env_path)
        print(f"已加载环境变量文件: {env_path}")

# 数据库配置
DB_FILE = Path(__file__).parent / "webhook_server.db"

# 任务配置
CHECK_INTERVAL = 1  # 检查间隔（秒）
TASK_TIMEOUT = 600  # 任务超时时间（秒）
MAX_RETRIES = 3  # 最大重试次数
