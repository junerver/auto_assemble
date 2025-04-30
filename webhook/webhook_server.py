import logging

from flask import Flask, render_template

from .config import PORT, DEBUG, DB_FILE
from .controllers import (
    webhook_bp,
    project_bp,
    task_bp,
    third_party_bp,
    auth_bp,
    events_bp,
    metadata_bp,
)
from .extensions.context import init_app
from .extensions.sse import ServerSentEvents
from .models.database import init_db


def create_app():
    """创建Flask应用"""
    app = Flask(__name__, template_folder="templates")

    # 配置数据库文件路径
    app.config["DB_FILE"] = DB_FILE
    app.config["PORT"] = PORT

    # 初始化数据库
    init_db()

    # 初始化数据库连接管理
    init_app(app)

    # 初始化 SSE 扩展
    ServerSentEvents(app)

    # 注册蓝图
    app.register_blueprint(webhook_bp)
    app.register_blueprint(project_bp, url_prefix="/api/config")
    app.register_blueprint(task_bp)
    app.register_blueprint(third_party_bp, url_prefix="/api/config/third-party")
    app.register_blueprint(auth_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(metadata_bp, url_prefix="/api/metadata")

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
    _app = create_app()
    # 运行应用
    _app.run(host="0.0.0.0", port=PORT, ssl_context=None, debug=DEBUG, use_reloader=DEBUG)
