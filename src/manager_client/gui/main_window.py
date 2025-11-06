"""
Main Window Module

This module provides the main GUI window for the manager client.
"""

import logging
import threading
import webbrowser
from typing import Optional, Callable

try:
    import customtkinter as ctk
except ImportError:
    ctk = None

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    # 尝试导入 CEF 用于嵌入式浏览器
    from cefpython3 import cefpython as cef

    CEF_AVAILABLE = True
except ImportError:
    CEF_AVAILABLE = False
    cef = None

import requests


class MainWindow:
    """主窗口类"""

    def __init__(
        self, master, server_url: str, show_statistics_callback: Callable, event_manager: Optional[object] = None
    ):
        self.master = master
        self.server_url = server_url
        self.show_statistics_callback = show_statistics_callback
        self.event_manager = event_manager

        self.setup_ui()
        self.setup_status()

    def setup_ui(self):
        """设置用户界面"""
        # 主框架
        self.main_frame = ctk.CTkFrame(self.master)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # 顶部工具栏
        self.setup_toolbar()

        # 内容区域
        self.setup_content_area()

        # 底部状态栏
        self.setup_status_bar()

    def setup_toolbar(self):
        """设置工具栏"""
        toolbar_frame = ctk.CTkFrame(self.main_frame)
        toolbar_frame.pack(fill="x", padx=5, pady=5)

        # 标题
        title_label = ctk.CTkLabel(toolbar_frame, text="构建管理客户端", font=ctk.CTkFont(size=20, weight="bold"))
        title_label.pack(side="left", padx=10)

        # 分隔符
        separator = ctk.CTkFrame(toolbar_frame, width=2)
        separator.pack(side="left", fill="y", padx=10)

        # 统计按钮
        self.stats_button = ctk.CTkButton(
            toolbar_frame, text="📊 查看统计", command=self.show_statistics_callback, width=120
        )
        self.stats_button.pack(side="left", padx=5)

        # 刷新按钮
        self.refresh_button = ctk.CTkButton(toolbar_frame, text="🔄 刷新", command=self.refresh_content, width=80)
        self.refresh_button.pack(side="left", padx=5)

        # 设置按钮
        self.settings_button = ctk.CTkButton(toolbar_frame, text="⚙️ 设置", command=self.show_settings, width=80)
        self.settings_button.pack(side="left", padx=5)

        # 右侧信息
        info_frame = ctk.CTkFrame(toolbar_frame)
        info_frame.pack(side="right", padx=10)

        self.server_label = ctk.CTkLabel(info_frame, text=f"服务器: {self.server_url}", font=ctk.CTkFont(size=12))
        self.server_label.pack(side="left", padx=5)

    def setup_content_area(self):
        """设置内容区域"""
        content_frame = ctk.CTkFrame(self.main_frame)
        content_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # 标签页
        self.tabview = ctk.CTkTabview(content_frame)
        self.tabview.pack(fill="both", expand=True)

        # 看板标签页
        self.dashboard_tab = self.tabview.add("📊 看板")
        self.setup_dashboard_tab()

        # 日志标签页
        self.logs_tab = self.tabview.add("📋 日志")
        self.setup_logs_tab()

        # 连接状态标签页
        self.connection_tab = self.tabview.add("🔗 连接状态")
        self.setup_connection_tab()

    def setup_dashboard_tab(self):
        """设置看板标签页"""
        # 如果 CEF 可用，使用嵌入式浏览器
        if CEF_AVAILABLE:
            self.setup_embedded_browser()
        else:
            # 使用系统默认浏览器打开看板
            self.setup_web_dashboard()

    def setup_embedded_browser(self):
        """设置嵌入式浏览器"""
        try:
            # 信息框架
            info_frame = ctk.CTkFrame(self.dashboard_tab)
            info_frame.pack(fill="x", padx=10, pady=10)

            info_label = ctk.CTkLabel(
                info_frame, text="🌐 构建看板 (嵌入式浏览器)", font=ctk.CTkFont(size=14, weight="bold")
            )
            info_label.pack(side="left", padx=10)

            open_browser_btn = ctk.CTkButton(
                info_frame, text="在外部浏览器中打开", command=self.open_dashboard_in_browser
            )
            open_browser_btn.pack(side="right", padx=10)

            # CEF 浏览器容器
            browser_frame = ctk.CTkFrame(self.dashboard_tab)
            browser_frame.pack(fill="both", expand=True, padx=10, pady=5)

            # 这里可以集成 CEF 浏览器
            # 由于 CEF 集成较复杂，暂时使用外部浏览器
            self.setup_web_dashboard_placeholder(browser_frame)

        except Exception as e:
            logging.error(f"设置嵌入式浏览器失败: {e}")
            self.setup_web_dashboard()

    def setup_web_dashboard_placeholder(self, parent):
        """设置网页看板占位符"""
        placeholder_frame = ctk.CTkFrame(parent)
        placeholder_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # 创建看板预览
        preview_frame = ctk.CTkFrame(placeholder_frame)
        preview_frame.pack(fill="both", expand=True)

        # 看板信息
        info_frame = ctk.CTkFrame(preview_frame)
        info_frame.pack(fill="x", padx=20, pady=20)

        title_label = ctk.CTkLabel(info_frame, text="📊 构建管理看板", font=ctk.CTkFont(size=18, weight="bold"))
        title_label.pack(pady=10)

        url_label = ctk.CTkLabel(info_frame, text=f"访问地址: {self.server_url}", font=ctk.CTkFont(size=12))
        url_label.pack(pady=5)

        # 操作按钮
        button_frame = ctk.CTkFrame(info_frame)
        button_frame.pack(pady=20)

        open_btn = ctk.CTkButton(
            button_frame, text="🌐 在浏览器中打开看板", command=self.open_dashboard_in_browser, width=200
        )
        open_btn.pack(pady=10)

        refresh_btn = ctk.CTkButton(
            button_frame, text="🔄 刷新连接状态", command=self.check_server_connection, width=200
        )
        refresh_btn.pack(pady=5)

        # 连接状态显示
        self.connection_status_label = ctk.CTkLabel(info_frame, text="检查连接状态中...", font=ctk.CTkFont(size=11))
        self.connection_status_label.pack(pady=10)

        # 启动连接检查
        self.check_server_connection()

    def setup_web_dashboard(self):
        """设置网页看板"""
        info_frame = ctk.CTkFrame(self.dashboard_tab)
        info_frame.pack(fill="both", expand=True, padx=20, pady=20)

        title_label = ctk.CTkLabel(info_frame, text="📊 构建管理看板", font=ctk.CTkFont(size=18, weight="bold"))
        title_label.pack(pady=20)

        description_label = ctk.CTkLabel(
            info_frame, text="点击下方按钮在默认浏览器中打开构建管理看板", font=ctk.CTkFont(size=12)
        )
        description_label.pack(pady=10)

        button_frame = ctk.CTkFrame(info_frame)
        button_frame.pack(pady=30)

        open_btn = ctk.CTkButton(
            button_frame, text="🌐 打开管理看板", command=self.open_dashboard_in_browser, width=250, height=50
        )
        open_btn.pack(pady=10)

        self.connection_status_label = ctk.CTkLabel(info_frame, text="检查连接状态中...", font=ctk.CTkFont(size=11))
        self.connection_status_label.pack(pady=10)

        # 启动连接检查
        self.check_server_connection()

    def setup_logs_tab(self):
        """设置日志标签页"""
        # 日志框架
        logs_frame = ctk.CTkFrame(self.logs_tab)
        logs_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # 日志标题和控制
        control_frame = ctk.CTkFrame(logs_frame)
        control_frame.pack(fill="x", padx=5, pady=5)

        logs_label = ctk.CTkLabel(control_frame, text="📋 实时日志", font=ctk.CTkFont(size=14, weight="bold"))
        logs_label.pack(side="left", padx=10)

        clear_btn = ctk.CTkButton(control_frame, text="清空日志", command=self.clear_logs, width=80)
        clear_btn.pack(side="right", padx=5)

        # 日志文本区域
        self.logs_textbox = ctk.CTkTextbox(logs_frame)
        self.logs_textbox.pack(fill="both", expand=True, padx=5, pady=5)

        # 配置日志处理器
        self.setup_log_handler()

    def setup_connection_tab(self):
        """设置连接状态标签页"""
        connection_frame = ctk.CTkFrame(self.connection_tab)
        connection_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # 连接信息
        info_frame = ctk.CTkFrame(connection_frame)
        info_frame.pack(fill="x", padx=20, pady=20)

        title_label = ctk.CTkLabel(info_frame, text="🔗 连接状态", font=ctk.CTkFont(size=16, weight="bold"))
        title_label.pack(pady=10)

        # 连接详情
        self.sse_status_label = ctk.CTkLabel(info_frame, text="SSE 连接: 检查中...", font=ctk.CTkFont(size=12))
        self.sse_status_label.pack(pady=5)

        self.last_update_label = ctk.CTkLabel(info_frame, text="最后更新: --", font=ctk.CTkFont(size=11))
        self.last_update_label.pack(pady=5)

        # 刷新按钮
        refresh_frame = ctk.CTkFrame(connection_frame)
        refresh_frame.pack(fill="x", padx=20, pady=10)

        refresh_btn = ctk.CTkButton(refresh_frame, text="🔄 检查连接", command=self.check_connection_status, width=150)
        refresh_btn.pack(pady=10)

    def setup_status_bar(self):
        """设置状态栏"""
        status_frame = ctk.CTkFrame(self.main_frame)
        status_frame.pack(fill="x", padx=5, pady=5)

        self.status_label = ctk.CTkLabel(status_frame, text="就绪", font=ctk.CTkFont(size=11))
        self.status_label.pack(side="left", padx=10)

        # 版本信息
        version_label = ctk.CTkLabel(status_frame, text="v1.0.0", font=ctk.CTkFont(size=10))
        version_label.pack(side="right", padx=10)

    def setup_status(self):
        """设置状态"""
        self.update_status("应用启动完成")
        self.update_connection_status("连接中...")

    def setup_log_handler(self):
        """设置日志处理器"""

        class GUILogHandler(logging.Handler):
            def __init__(self, textbox):
                super().__init__()
                self.textbox = textbox

            def emit(self, record):
                try:
                    msg = self.format(record)
                    # 在主线程中更新 GUI
                    self.textbox.after(0, lambda: self._update_textbox(msg))
                except Exception:
                    pass

            def _update_textbox(self, msg):
                self.textbox.insert("end", msg + "\n")
                self.textbox.see("end")

        # 创建并添加 GUI 日志处理器
        self.gui_log_handler = GUILogHandler(self.logs_textbox)
        self.gui_log_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        logging.getLogger().addHandler(self.gui_log_handler)

    def update_status(self, message: str):
        """更新状态栏"""
        if hasattr(self, "status_label"):
            self.status_label.configure(text=message)

    def update_connection_status(self, status: str):
        """更新连接状态"""
        if hasattr(self, "sse_status_label"):
            self.sse_status_label.configure(text=f"SSE 连接: {status}")

    def clear_logs(self):
        """清空日志"""
        if hasattr(self, "logs_textbox"):
            self.logs_textbox.delete("1.0", "end")

    def refresh_content(self):
        """刷新内容"""
        self.update_status("刷新中...")
        self.check_server_connection()
        self.check_connection_status()
        self.update_status("刷新完成")

    def check_server_connection(self):
        """检查服务器连接"""

        def check():
            try:
                response = requests.get(f"{self.server_url}/api/task/statistics", timeout=5)
                if response.status_code == 200:
                    status = "✅ 连接正常"
                else:
                    status = f"❌ 服务异常 ({response.status_code})"
            except Exception as e:
                status = f"❌ 连接失败: {str(e)}"

            if hasattr(self, "connection_status_label"):
                self.connection_status_label.configure(text=status)

        # 在后台线程中检查
        threading.Thread(target=check, daemon=True).start()

    def check_connection_status(self):
        """检查连接状态"""
        if self.event_manager:
            if self.event_manager.running:
                self.update_connection_status("✅ 已连接")
            else:
                self.update_connection_status("❌ 未连接")
        else:
            self.update_connection_status("❌ 未初始化")

        # 更新最后更新时间
        from datetime import datetime

        now = datetime.now().strftime("%H:%M:%S")
        if hasattr(self, "last_update_label"):
            self.last_update_label.configure(text=f"最后更新: {now}")

    def open_dashboard_in_browser(self):
        """在浏览器中打开看板"""
        try:
            webbrowser.open(self.server_url)
            self.update_status("已打开管理看板")
        except Exception as e:
            logging.error(f"打开浏览器失败: {e}")
            self.update_status("打开浏览器失败")

    def show_settings(self):
        """显示设置"""
        # TODO: 实现设置窗口
        self.update_status("设置功能开发中...")
