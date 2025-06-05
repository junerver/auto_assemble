"""
Manager Client Main Module

This module provides the main entry point for the manager client.
"""

import asyncio
import logging
import sys

from manager_client.client import EventManager
from manager_client.config import SERVER_HOST_URL
from manager_client.notifications import show_toast


def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )


def handle_toast(data: dict):
    """处理 toast 事件"""
    title = data.get("title", "通知")
    message = data.get("message", "")
    show_toast(title, message)


async def run_manager():
    """运行管理器"""
    manager = EventManager(SERVER_HOST_URL)
    manager.on("toast", handle_toast)
    manager.start()

    try:
        # 保持程序运行
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logging.info("Shutting down manager client")
        manager.stop()


def main():
    """主函数"""
    setup_logging()
    logging.info("Starting manager client")

    try:
        asyncio.run(run_manager())
    except KeyboardInterrupt:
        logging.info("Manager client stopped by user")
    except Exception as e:
        logging.exception(f"Error running manager client: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
