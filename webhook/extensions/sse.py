"""
SSE Extension

This module provides Server-Sent Events (SSE) functionality for the webhook server.
"""

import json
import logging
from queue import Queue
from typing import List

from flask import Response, stream_with_context


class ServerSentEvents:
    """Server-Sent Events 扩展"""

    def __init__(self, app=None):
        self.app = app
        self.clients: List[Queue] = []
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """初始化扩展"""
        app.extensions["sse"] = self

    def publish(self, event_type: str, data: dict):
        """广播事件到所有客户端"""
        message = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
        logging.info(f"Publishing: {message.strip()}")
        logging.info(f"Current clients: {len(self.clients)}")

        # 清理无效的客户端
        valid_clients = []
        for client_queue in self.clients:
            try:
                # 测试客户端是否仍然有效
                client_queue.put(":\n\n", block=False)  # 发送心跳消息
                valid_clients.append(client_queue)
            except Exception as e:
                logging.error(f"Removing invalid client: {e}")

        self.clients = valid_clients
        logging.info(f"Valid clients after cleanup: {len(self.clients)}")

        # 发送事件到所有有效客户端
        for client_queue in self.clients:
            try:
                client_queue.put(message)
                logging.info(f"Event sent to client successfully")
            except Exception as e:
                logging.error(f"Error sending event to client: {e}")
                self.clients.remove(client_queue)

    def stream(self):
        """SSE 流处理"""
        client_queue = Queue()
        self.clients.append(client_queue)
        logging.info(f"New client connected: {len(self.clients)} clients total")

        def generate():
            try:
                yield ":\n\n"  # 防止某些浏览器连接断开
                while True:
                    message = client_queue.get()
                    yield message
            except GeneratorExit:
                logging.info("Client disconnected")
            finally:
                # 清理客户端
                if client_queue in self.clients:
                    self.clients.remove(client_queue)
                    logging.info(f"Client removed: {len(self.clients)} clients remaining")

        return Response(
            stream_with_context(generate()),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )
