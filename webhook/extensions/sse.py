"""
SSE Extension

This module provides Server-Sent Events (SSE) functionality for the webhook server.
"""

import json
import logging
import queue
import time
from queue import Queue
from threading import Lock, Event
from typing import Dict, Set

from flask import Flask, Response, current_app, stream_with_context


class ServerSentEvents:
    """Server-Sent Events 扩展"""

    def __init__(self, app: Flask = None):
        self.app = app
        self.clients: Dict[str, Queue] = {}
        self.active_clients: Set[str] = set()
        self._lock = Lock()
        self._client_id_counter = 0
        self._stop_event = Event()
        self._heartbeat_interval = 15  # 心跳间隔（秒）
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask):
        """初始化扩展"""
        app.extensions["sse"] = self

    def _get_next_client_id(self) -> str:
        """获取下一个客户端ID"""
        with self._lock:
            self._client_id_counter += 1
            return f"client_{self._client_id_counter}"

    def publish(self, event_type: str, data: dict):
        """广播事件到所有客户端"""
        message = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
        logging.info(f"Publishing: {message.strip()}")

        with self._lock:
            clients_to_remove = set()
            active_clients = self.active_clients.copy()

            for client_id in active_clients:
                if client_id not in self.clients:
                    continue

                client_queue = self.clients[client_id]
                try:
                    # 使用非阻塞方式发送消息
                    client_queue.put_nowait(message)
                    logging.info(f"Event sent to client {client_id} successfully")
                except queue.Full:
                    logging.warning(f"Client {client_id} queue is full, removing client")
                    clients_to_remove.add(client_id)
                except Exception as e:
                    logging.error(f"Unexpected error sending event to client {client_id}: {e}")
                    clients_to_remove.add(client_id)

            # 批量移除无效客户端
            for client_id in clients_to_remove:
                try:
                    del self.clients[client_id]
                    self.active_clients.discard(client_id)
                    logging.info(
                        f"Client {client_id} removed: {len(self.clients)} clients remaining"
                    )
                except KeyError:
                    pass

    def stream(self):
        """SSE 流处理"""
        client_id = self._get_next_client_id()
        client_queue = Queue(maxsize=10)  # 减小队列大小

        with self._lock:
            self.clients[client_id] = client_queue
            self.active_clients.add(client_id)
        logging.info(f"New client {client_id} connected: {len(self.clients)} clients total")

        def generate():
            last_heartbeat = time.time()
            try:
                # 发送初始心跳
                yield ":\n\n"
                while not self._stop_event.is_set():
                    try:
                        # 使用较短的超时时间
                        message = client_queue.get(
                            timeout=1
                        )  # 使用更短的超时时间，更频繁地检查心跳
                        last_heartbeat = time.time()
                        yield message
                    except queue.Empty:
                        current_time = time.time()
                        # 检查是否需要发送心跳
                        if current_time - last_heartbeat >= self._heartbeat_interval:
                            # 发送心跳保持连接
                            yield ":\n\n"
                            # 重置心跳时间戳
                            last_heartbeat = current_time
                            logging.debug(f"Sent heartbeat to client {client_id}")
            except GeneratorExit:
                logging.info(f"Client {client_id} disconnected")
            finally:
                # 清理客户端
                with self._lock:
                    try:
                        del self.clients[client_id]
                        self.active_clients.discard(client_id)
                        logging.info(
                            f"Client {client_id} removed: {len(self.clients)} clients remaining"
                        )
                    except KeyError:
                        pass

        response = Response(
            stream_with_context(generate()),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

        # 设置响应超时
        response.timeout = None
        return response

    def shutdown(self):
        """关闭所有SSE连接"""
        self._stop_event.set()
        with self._lock:
            self.clients.clear()
            self.active_clients.clear()

    @staticmethod
    def publish_event(event_type: str, data: dict):
        """发布事件"""
        if hasattr(current_app, "extensions") and "sse" in current_app.extensions:
            current_app.extensions["sse"].publish(event_type, data)
        else:
            raise RuntimeError("SSE extension not initialized")

    @staticmethod
    def get_stream():
        """获取流"""
        if hasattr(current_app, "extensions") and "sse" in current_app.extensions:
            return current_app.extensions["sse"].stream()
        else:
            raise RuntimeError("SSE extension not initialized")
