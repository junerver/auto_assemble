"""
Manager Client Main Module

This module provides the main entry point for the manager client.
Supports both GUI and CLI modes.
"""

import asyncio
import logging
import sys
import os

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


def run_gui_mode():
    """运行 GUI 模式"""
    try:
        from manager_client.gui_main import main as gui_main

        gui_main()
    except ImportError as e:
        logging.error(f"GUI 模式需要 customtkinter 依赖: {e}")
        logging.error("请安装依赖: uv sync --extra dev")
        sys.exit(1)


async def run_cli_mode():
    """运行 CLI 模式"""
    from manager_client.client import EventManager

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

    # 检查是否有 GUI 环境和相关依赖
    has_gui = True
    try:
        # 检查是否在支持的平台上
        if sys.platform == "win32":
            # Windows 平面，默认使用 GUI
            pass
        elif sys.platform.startswith("linux"):
            # 检查是否有 DISPLAY 环境变量
            if not os.environ.get("DISPLAY"):
                has_gui = False
        elif sys.platform == "darwin":
            # macOS，支持 GUI
            pass
        else:
            has_gui = False

        # 尝试导入 customtkinter
        if has_gui:
            import importlib.util

            if importlib.util.find_spec("customtkinter"):
                pass
            else:
                has_gui = False
    except ImportError:
        has_gui = False

    # 根据环境选择运行模式
    if has_gui:
        try:
            logging.info("Starting in GUI mode")
            run_gui_mode()
        except Exception as e:
            logging.error(f"GUI mode failed: {e}")
            logging.info("Falling back to CLI mode")
            try:
                asyncio.run(run_cli_mode())
            except Exception as cli_error:
                logging.exception(f"CLI mode also failed: {cli_error}")
                sys.exit(1)
    else:
        try:
            logging.info("Starting in CLI mode")
            asyncio.run(run_cli_mode())
        except Exception as e:
            logging.exception(f"Error running manager client: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
