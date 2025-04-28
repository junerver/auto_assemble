import sqlite3

from flask import g, current_app


def get_db():
    """获取数据库连接"""
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DB_FILE"])
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db():
    """关闭数据库连接"""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_app(app):
    """初始化应用"""
    app.teardown_appcontext(close_db)
