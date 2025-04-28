"""
Client Module

This module provides SSE client functionality for the manager client.
"""

import asyncio
import json
import logging
from typing import Callable, Dict
from urllib.parse import urljoin

import aiohttp

from .config import SERVER_HOST_URL, RECONNECT_INTERVAL


class EventManager:
    """事件管理器，用于处理 SSE 事件"""

    def __init__(self, base_url: str = SERVER_HOST_URL):
        self.base_url = base_url
        self.event_handlers: Dict[str, Callable] = {}
        self.session = None
        self.running = False
        self._task = None

    async def connect(self):
        """连接到 SSE 服务器"""
        while True:
            try:
                logging.info(f"Connecting to SSE server at {self.base_url}")
                async with aiohttp.ClientSession() as session:
                    self.session = session
                    async with session.get(
                        urljoin(self.base_url, "/events"),
                        headers={"Accept": "text/event-stream"},
                        timeout=aiohttp.ClientTimeout(total=None),
                    ) as response:
                        logging.info(f"Response status: {response.status}")
                        logging.info(f"Response headers: {response.headers}")

                        if response.status != 200:
                            logging.error(f"Unexpected status code: {response.status}")
                            await asyncio.sleep(RECONNECT_INTERVAL)
                            continue

                        if "text/event-stream" not in response.headers.get(
                                "Content-Type", ""
                        ):
                            logging.error(
                                f"Unexpected content type: {response.headers.get('Content-Type')}"
                            )
                            await asyncio.sleep(RECONNECT_INTERVAL)
                            continue

                        self.running = True
                        logging.info("Connected to SSE server")

                        async for line in response.content:
                            if not self.running:
                                logging.info("SSE connection closed")
                                break

                            try:
                                line = line.decode("utf-8").strip()
                                if not line:
                                    continue

                                logging.info(f"Received line: {line}")

                                if line.startswith("event:"):
                                    event_type = line[6:].strip()
                                    logging.info(f"Event type: {event_type}")
                                elif line.startswith("data:"):
                                    data = json.loads(line[5:].strip())
                                    logging.info(f"Event data: {data}")

                                    if event_type in self.event_handlers:
                                        logging.info(f"Processing event: {event_type}")
                                        self.event_handlers[event_type](data)
                                    else:
                                        logging.warning(
                                            f"No handler registered for event type: {event_type}"
                                        )
                            except Exception as e:
                                logging.error(f"Error processing event: {e}")
                                logging.exception("Full error details:")

            except aiohttp.ClientError as e:
                logging.error(f"SSE connection error: {e}")
                logging.exception("Full error details:")
                if not self.running:
                    break
                await asyncio.sleep(RECONNECT_INTERVAL)
            except Exception as e:
                logging.error(f"Unexpected error in SSE connection: {e}")
                logging.exception("Full error details:")
                if not self.running:
                    break
                await asyncio.sleep(RECONNECT_INTERVAL)

    def disconnect(self):
        """断开 SSE 连接"""
        logging.info("Disconnecting from SSE server")
        self.running = False
        if self.session:
            self.session.close()
            self.session = None

    def on(self, event_type: str, handler: Callable):
        """注册事件处理器"""
        self.event_handlers[event_type] = handler
        logging.info(f"Registered handler for event type: {event_type}")

    def start(self):
        """启动事件管理器"""
        if not self.running:
            self.running = True
            # 获取当前事件循环
            loop = asyncio.get_event_loop()
            # 创建并启动任务
            self._task = loop.create_task(self.connect())

    def stop(self):
        """停止事件管理器"""
        self.disconnect()
        if self._task:
            self._task.cancel()
            self._task = None
