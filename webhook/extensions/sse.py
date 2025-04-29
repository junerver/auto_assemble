"""
SSE Extension

This module provides Server-Sent Events (SSE) functionality for the webhook server.
"""

import json
import logging
import queue
import time
from queue import Queue
from threading import Lock
from typing import List

from flask import Response, stream_with_context


class ServerSentEvents:
    """Server-Sent Events 扩展"""

    def __init__(self, app=None):
        self.app = app
        self.clients: List[Queue] = []
        self._lock = Lock()  # 添加锁
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """初始化扩展"""
        app.extensions["sse"] = self

    def publish(self, event_type: str, data: dict):
        """广播事件到所有客户端"""
        message = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
        logging.info(f"Publishing: {message.strip()}")

        with self._lock:
            clients_to_remove = []
            for client_queue in self.clients:
                try:
                    client_queue.put(message, timeout=1.0)
                    logging.info("Event sent to client successfully")
                except queue.Full:
                    logging.warning("Client queue is full, removing client")
                    clients_to_remove.append(client_queue)
                except Exception as e:
                    logging.error(f"Unexpected error sending event to client: {e}")
                    clients_to_remove.append(client_queue)

            # 批量移除无效客户端
            for client in clients_to_remove:
                try:
                    self.clients.remove(client)
                except ValueError:
                    pass

    def stream(self):
        """SSE 流处理"""
        # 设置队列最大大小
        client_queue = Queue(maxsize=100)
        with self._lock:
            self.clients.append(client_queue)
        logging.info(f"New client connected: {len(self.clients)} clients total")

        def generate():
            last_heartbeat = time.time()
            try:
                # 发送初始心跳
                yield ":\n\n"
                while True:
                    try:
                        # 设置超时，避免永久阻塞
                        message = client_queue.get(timeout=30.0)
                        last_heartbeat = time.time()
                        yield message
                    except Exception:
                        # 检查心跳超时
                        if time.time() - last_heartbeat > 60:  # 60秒无响应视为断开
                            raise TimeoutError("Client heartbeat timeout")
                        # 发送心跳保持连接
                        yield ":\n\n"
            except (GeneratorExit, TimeoutError):
                logging.info("Client disconnected")
            finally:
                # 清理客户端
                with self._lock:
                    try:
                        self.clients.remove(client_queue)
                        logging.info(f"Client removed: {len(self.clients)} clients remaining")
                    except ValueError:
                        pass

        return Response(
            stream_with_context(generate()),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )
