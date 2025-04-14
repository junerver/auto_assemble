import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, render_template

from webhook.config import PORT, DEBUG
from webhook.controllers import webhook_bp, project_bp, task_bp, third_party_bp
from webhook.models.database import init_db

# 加载环境变量
env_path = Path(os.path.dirname(os.path.abspath(__file__))) / ".env"
if not env_path.exists():
    logging.error(f"环境变量文件 '{env_path}' 不存在")
else:
    load_dotenv(env_path)
    logging.info(f"已加载环境变量文件: {env_path}")

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("webhook.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)


def create_app():
    """创建Flask应用"""
    app = Flask(__name__, template_folder="templates")

    # 初始化数据库
    init_db()

    # 注册蓝图
    app.register_blueprint(webhook_bp, url_prefix="/api")
    app.register_blueprint(project_bp, url_prefix="/api")
    app.register_blueprint(task_bp, url_prefix="/api")
    app.register_blueprint(third_party_bp, url_prefix="/api")

    # 打印所有注册的路由
    logging.info("已注册的路由:")
    for rule in app.url_map.iter_rules():
        logging.info(f"Route: {rule.endpoint} -> {rule}")

    # 配置热更新
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

    @app.route("/")
    def index():
        """显示打包服务器状态页面"""
        return render_template("index.html")

    return app


if __name__ == "__main__":
    # 创建应用
    app = create_app()

    # 运行应用
    app.run(host="0.0.0.0", port=PORT, ssl_context=None, debug=DEBUG, use_reloader=DEBUG)
