import logging
import os
from pathlib import Path

from dotenv import load_dotenv

DISTRIBUTION_PATH = os.getenv("DISTRIBUTION_PATH")
ANDROID_UNI_BASE_PATH = os.getenv("ANDROID_UNI_BASE_PATH")
SERVER_HOST_URL = os.getenv("SERVER_HOST_URL")

# 打印当前环境变量状态
logging.info(
    f"当前环境变量：\nDISTRIBUTION_PATH: {DISTRIBUTION_PATH}\nANDROID_UNI_BASE_PATH: {ANDROID_UNI_BASE_PATH}\nSERVER_HOST_URL: {SERVER_HOST_URL}"
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
        logging.info(f"环境变量文件 '{env_path}' 不存在")
    else:
        load_dotenv(env_path)
        logging.info(f"已加载环境变量文件: {env_path}")
        DISTRIBUTION_PATH = os.getenv("DISTRIBUTION_PATH")
        ANDROID_UNI_BASE_PATH = os.getenv("ANDROID_UNI_BASE_PATH")
        SERVER_HOST_URL = os.getenv("SERVER_HOST_URL")
