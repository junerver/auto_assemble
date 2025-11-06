"""
GUI Manager Client Main Module

This module provides the main GUI entry point for the manager client using customtkinter.
"""

import asyncio
import logging
import threading
from tkinter import messagebox
from typing import Optional

try:
    import customtkinter as ctk
except ImportError:
    ctk = None

from manager_client.client import EventManager
from manager_client.config import SERVER_HOST_URL
from manager_client.notifications import show_toast
from manager_client.gui.main_window import MainWindow
from manager_client.gui.statistics_window import StatisticsWindow


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


class ManagerGUI:
    """管理客户端 GUI 主类"""

    def __init__(self):
        if ctk is None:
            raise ImportError("customtkinter is required for GUI mode. Please install with: pip install customtkinter")

        self.app: Optional[ctk.CTk] = None
        self.main_window: Optional[MainWindow] = None
        self.event_manager: Optional[EventManager] = None
        self.running = False
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.sse_thread: Optional[threading.Thread] = None

    def setup_appearance(self):
        """设置应用外观"""
        ctk.set_appearance_mode("dark")  # 暗色主题
        ctk.set_default_color_theme("blue")  # 蓝色主题

    def create_gui(self):
        """创建 GUI 界面"""
        self.app = ctk.CTk()
        self.app.title("构建管理客户端")
        self.app.geometry("1200x800")
        self.app.minsize(800, 600)

        # 设置窗口图标和关闭行为
        self.app.protocol("WM_DELETE_WINDOW", self.on_closing)

        # 创建主窗口
        self.main_window = MainWindow(
            master=self.app,
            server_url=SERVER_HOST_URL,
            show_statistics_callback=self.show_statistics,
            event_manager=self.event_manager,
        )

    def start_sse_client(self):
        """在单独线程中启动 SSE 客户端"""

        def run_sse():
            try:
                # 创建新的事件循环
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)

                # 启动事件管理器
                self.event_manager = EventManager(SERVER_HOST_URL)
                self.event_manager.on("toast", handle_toast)
                self.event_manager.start()

                # 保持运行
                self.loop.run_forever()
            except Exception as e:
                logging.error(f"SSE 客户端错误: {e}")
            finally:
                if self.loop and not self.loop.is_closed():
                    self.loop.close()

        self.sse_thread = threading.Thread(target=run_sse, daemon=True)
        self.sse_thread.start()

    def show_statistics(self):
        """显示统计窗口"""
        if self.main_window:
            StatisticsWindow(parent=self.app, server_url=SERVER_HOST_URL)

    def on_closing(self):
        """关闭窗口时的处理"""
        logging.info("正在关闭应用...")
        self.running = False

        # 停止 SSE 客户端
        if self.event_manager:
            self.event_manager.stop()

        # 停止事件循环
        if self.loop and not self.loop.is_closed():
            self.loop.call_soon_threadsafe(self.loop.stop)

        # 等待线程结束
        if self.sse_thread and self.sse_thread.is_alive():
            self.sse_thread.join(timeout=2)

        # 关闭 GUI
        if self.app:
            self.app.quit()
            self.app.destroy()

    def run(self):
        """运行应用"""
        try:
            # 设置外观
            self.setup_appearance()

            # 创建 GUI
            self.create_gui()

            # 启动 SSE 客户端
            self.start_sse_client()

            self.running = True

            # 运行 GUI 主循环
            self.app.mainloop()

        except Exception as e:
            logging.exception(f"运行 GUI 时发生错误: {e}")
            if ctk:
                messagebox.showerror("错误", f"启动应用失败: {str(e)}")


def main():
    """主函数"""
    setup_logging()
    logging.info("Starting manager client GUI")

    try:
        gui = ManagerGUI()
        gui.run()
    except KeyboardInterrupt:
        logging.info("Manager client stopped by user")
    except Exception as e:
        logging.exception(f"Error running manager client: {e}")
        # 在 GUI 不可用时的降级处理
        import sys

        sys.exit(1)


if __name__ == "__main__":
    main()
