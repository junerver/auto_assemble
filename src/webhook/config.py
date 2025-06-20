import logging
import textwrap

import colorlog
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

# 从环境变量读取配置
DISTRIBUTION_PATH = os.getenv("DISTRIBUTION_PATH")
ANDROID_UNI_BASE_PATH = os.getenv("ANDROID_UNI_BASE_PATH")
SERVER_HOST_URL = os.getenv("SERVER_HOST_URL")
PORT = int(os.getenv("PORT", 5005))
DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
API_TEST = os.getenv("API_TEST", "false").lower() == "true"


# 打印当前环境变量状态
print(
    f"当前环境变量：\nDISTRIBUTION_PATH: {DISTRIBUTION_PATH}\nANDROID_UNI_BASE_PATH: {ANDROID_UNI_BASE_PATH}\nSERVER_HOST_URL: {SERVER_HOST_URL}\nPORT: {PORT}\nDEBUG: {DEBUG}\nAPI_TEST: {API_TEST}"
)

# 检查必需的环境变量，存在下面的环境变量说明是docker容器启动（yaml指定环境变量）
# 这三个环境变量是auto_assemble、fork_task工具需要的，webhook服务不需要，所以不需要
# 在重载环境变量文件后覆盖
required_vars = {
    "DISTRIBUTION_PATH": DISTRIBUTION_PATH,
    "ANDROID_UNI_BASE_PATH": ANDROID_UNI_BASE_PATH,
    "SERVER_HOST_URL": SERVER_HOST_URL,
}

missing_vars = [var for var, value in required_vars.items() if value is None]
if missing_vars:
    env_path: Path = Path(__file__).parent / ".env"
    if not env_path.exists():
        print(f"环境变量文件 '{env_path}' 不存在")
    else:
        print(f"加载环境变量文件 '{env_path}'")
        load_dotenv(env_path)
        DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
        PORT = int(os.getenv("PORT", 5005))
        API_TEST = os.getenv("API_TEST", "false").lower() == "true"
        DISTRIBUTION_PATH = os.getenv("DISTRIBUTION_PATH")
        ANDROID_UNI_BASE_PATH = os.getenv("ANDROID_UNI_BASE_PATH")
        SERVER_HOST_URL = os.getenv("SERVER_HOST_URL")
        print(
            textwrap.dedent(f"""
            当前环境变量：
            DISTRIBUTION_PATH: {DISTRIBUTION_PATH}
            ANDROID_UNI_BASE_PATH: {ANDROID_UNI_BASE_PATH}
            SERVER_HOST_URL: {SERVER_HOST_URL}
            PORT: {PORT}
            DEBUG: {DEBUG}
            API_TEST: {API_TEST}
            """)
        )

# 数据库配置
DB_FILE = Path(__file__).parent / "webhook_server.db"

# 任务配置
CHECK_INTERVAL = 1  # 检查间隔（秒）
TASK_TIMEOUT = 600  # 任务超时时间（秒）
MAX_RETRIES = 3  # 最大重试次数


def setup_logging(log_file: str = "webhook.log"):
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # ✅ 替换为 RotatingFileHandler
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

    # 彩色控制台日志
    console_handler = colorlog.StreamHandler()
    console_handler.setFormatter(
        colorlog.ColoredFormatter(
            "%(log_color)s%(asctime)s - %(levelname)s - %(message)s",
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "red,bg_white",
            },
        )
    )

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
