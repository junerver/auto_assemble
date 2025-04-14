import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from webhook.config import PORT, DEBUG
from webhook.webhook_server import create_app

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("webhook.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

# 加载环境变量
env_path = Path(os.path.dirname(os.path.abspath(__file__))) / ".env"
if not env_path.exists():
    logging.error(f"环境变量文件 '{env_path}' 不存在")
else:
    load_dotenv(env_path)
    logging.info(f"已加载环境变量文件: {env_path}")

# 创建应用实例
app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, ssl_context=None, debug=DEBUG, use_reloader=DEBUG)
