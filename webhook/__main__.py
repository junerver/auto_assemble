import logging
import sys

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

# 创建应用实例
app = create_app()


def main():
    # 配置热更新
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
    app.run(host="0.0.0.0", port=PORT, ssl_context=None, debug=DEBUG, use_reloader=DEBUG)


if __name__ == "__main__":
    sys.exit(main())
