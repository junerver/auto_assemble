"""
Events Controller

This module provides event-related endpoints for the webhook server.
"""

import json
import logging

from flask import current_app, Response

from . import events_bp


@events_bp.route("/events")
def stream():
    """SSE 流端点"""
    logging.info("New SSE connection established")
    return current_app.extensions["sse"].stream()


@events_bp.route("/events/test")
def test():
    """测试端点"""
    logging.info("Test endpoint called")

    # 构建测试数据
    test_data = {"title": "测试", "message": "Hello, World!"}
    logging.info(f"Test data: {test_data}")

    # 发布事件
    current_app.extensions["sse"].publish("toast", test_data)

    # 返回测试结果
    return Response(
        json.dumps({"status": "success", "message": "Event published"}),
        mimetype="application/json",
    )
