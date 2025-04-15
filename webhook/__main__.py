import logging
import sys

import colorlog
from flask import request

from webhook.config import PORT, DEBUG
from webhook.webhook_server import create_app

# 禁用 Werkzeug 的默认日志记录器
logging.getLogger("werkzeug").disabled = True

# 配置日志
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 移除所有现有的处理器
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

# 文件处理器
file_handler = logging.FileHandler("webhook.log", encoding="utf-8")
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

# 控制台处理器（带颜色）
console_handler = colorlog.StreamHandler()
console_handler.setFormatter(
    colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s - %(levelname)s - %(message)s",
        datefmt=None,
        reset=True,
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red,bg_white",
        },
        secondary_log_colors={},
        style="%",
    )
)

# 添加处理器
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# 创建应用实例
app = create_app()


# 添加请求日志中间件
@app.before_request
def log_request_info():
    logger.info(f"{request.remote_addr} - - [{request.method}] {request.path}")


def main():
    # 配置热更新
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
    app.run(host="0.0.0.0", port=PORT, ssl_context=None, debug=DEBUG, use_reloader=DEBUG)


if __name__ == "__main__":
    sys.exit(main())
