"""
Description:
Author: 侯文君
Date: 2025-05-15 17:01:40
LastEditors: 侯文君
LastEditTime: 2025-05-15 17:01:45
"""

# db.py
import sqlite3

from fastapi import Request

from webhook.config import DB_FILE


def get_db_conn():
    conn = sqlite3.connect(DB_FILE)
    # 设置查表返回为Row，这是一个类似字典的对象，可以通过列名访问数据，实际使用时最好通过dict()方法转换为字典
    conn.row_factory = sqlite3.Row
    return conn


def get_db(request: Request):
    """从 request.state 获取数据库连接"""
    return request.state.db
