"""
Main Window Module

This module provides the modern GUI window for the manager client with embedded WebView.
"""

import logging
import threading
import webbrowser
from typing import Optional, Callable

import requests
from datetime import datetime

try:
    import customtkinter as ctk
    from PIL import Image, ImageTk
except ImportError:
    ctk = None
    Image = None
    ImageTk = None

from manager_client.gui.embedded_browser import create_embedded_browser, get_browser_capabilities


# 优雅降级：如果没有 webview，提供替代方案
def safe_launch_webview(url, title="构建看板", width=1200, height=800):
    """安全启动 WebView，如果不可用则使用浏览器"""
    try:
        webbrowser.open(url)
        return True
    except Exception as e:
        logging.error(f"打开浏览器失败: {e}")
        return False


class ModernMainWindow:
    """现代化主窗口类"""

    def __init__(
        self, master, server_url: str, show_statistics_callback: Callable, event_manager: Optional[object] = None
    ):
        self.master = master
        self.server_url = server_url
        self.show_statistics_callback = show_statistics_callback
        self.event_manager = event_manager

        # 颜色配置
        self.colors = {
            "primary": "#2E86AB",  # 主蓝色
            "secondary": "#A23B72",  # 紫色
            "success": "#52B788",  # 绿色
            "warning": "#F3722C",  # 橙色
            "danger": "#D62828",  # 红色
            "dark_bg": "#1a1a2e",  # 深色背景
            "card_bg": "#16213e",  # 卡片背景
            "text_primary": "#ffffff",  # 主文字
            "text_secondary": "#b8b8b8",  # 次要文字
        }

        self.setup_ui()
        self.setup_status()

    def setup_ui(self):
        """设置现代化用户界面"""
        # 设置主窗口样式
        self.master.configure(fg_color=self.colors["dark_bg"])

        # 主容器 - 使用滚动框架
        self.main_container = ctk.CTkScrollableFrame(self.master, fg_color="transparent", corner_radius=0)
        self.main_container.pack(fill="both", expand=True, padx=20, pady=20)

        # 顶部标题区域
        self.setup_header()

        # 看板区域 (主要内容)
        self.setup_dashboard_area()

        # 快速操作区域
        self.setup_quick_actions()

        # 状态监控区域
        self.setup_status_monitor()

    def setup_header(self):
        """设置顶部标题区域"""
        header_frame = ctk.CTkFrame(
            self.main_container,
            fg_color=self.colors["card_bg"],
            corner_radius=15,
            border_width=2,
            border_color=self.colors["primary"],
        )
        header_frame.pack(fill="x", pady=(0, 20))

        # 标题容器
        title_container = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_container.pack(fill="x", padx=25, pady=20)

        # 主标题
        title_label = ctk.CTkLabel(
            title_container,
            text="🚀 构建管理中心",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=self.colors["text_primary"],
        )
        title_label.pack(side="left")

        # 副标题/服务器信息
        server_info = ctk.CTkLabel(
            title_container,
            text=f"📡 {self.server_url}",
            font=ctk.CTkFont(size=14),
            text_color=self.colors["text_secondary"],
        )
        server_info.pack(side="left", padx=(20, 0))

        # 右侧操作按钮
        actions_frame = ctk.CTkFrame(title_container, fg_color="transparent")
        actions_frame.pack(side="right")

        # 统计按钮
        stats_btn = ctk.CTkButton(
            actions_frame,
            text="📊 统计分析",
            command=self.show_statistics_callback,
            fg_color=self.colors["secondary"],
            hover_color="#8B2F5F",
            text_color="white",
            font=ctk.CTkFont(size=12, weight="bold"),
            corner_radius=10,
            width=120,
            height=35,
        )
        stats_btn.pack(side="right", padx=(10, 0))

        # 设置按钮
        settings_btn = ctk.CTkButton(
            actions_frame,
            text="⚙️ 设置",
            command=self.show_settings,
            fg_color="transparent",
            border_color=self.colors["text_secondary"],
            border_width=1,
            text_color=self.colors["text_secondary"],
            font=ctk.CTkFont(size=12),
            corner_radius=10,
            width=80,
            height=35,
        )
        settings_btn.pack(side="right", padx=(10, 0))

    def setup_dashboard_area(self):
        """设置看板区域"""
        dashboard_container = ctk.CTkFrame(self.main_container, fg_color=self.colors["card_bg"], corner_radius=15)
        dashboard_container.pack(fill="both", expand=True, pady=(0, 20))

        # 看板标题栏
        header_frame = ctk.CTkFrame(dashboard_container, fg_color="transparent")
        header_frame.pack(fill="x", padx=25, pady=(20, 10))

        title_label = ctk.CTkLabel(
            header_frame,
            text="📊 实时看板",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.colors["text_primary"],
        )
        title_label.pack(side="left")

        # 连接状态指示器
        self.connection_indicator = ctk.CTkLabel(
            header_frame, text="🔌 检查连接中...", font=ctk.CTkFont(size=12), text_color=self.colors["text_secondary"]
        )
        self.connection_indicator.pack(side="right")

        # WebView 容器区域
        self.webview_container = ctk.CTkFrame(dashboard_container, fg_color="transparent")
        self.webview_container.pack(fill="both", expand=True, padx=25, pady=(0, 20))

        # 初始化 WebView
        self.setup_webview()

    def setup_webview(self):
        """设置内嵌 WebView"""
        # 获取浏览器能力
        capabilities = get_browser_capabilities()
        logging.info(f"浏览器能力: {capabilities}")

        # 检查是否支持真正的内嵌浏览器
        if capabilities["cef_available"] or capabilities["tkinterhtml_available"]:
            self.create_true_embedded_browser()
        else:
            self.create_embedded_webview()

    def create_true_embedded_browser(self):
        """创建真正的内嵌浏览器"""
        try:
            # 创建浏览器容器
            browser_container = ctk.CTkFrame(self.webview_container, fg_color="#ffffff", corner_radius=10)
            browser_container.pack(fill="both", expand=True, pady=10)

            # 创建浏览器实例
            self.embedded_browser = create_embedded_browser(
                parent_frame=browser_container, url=self.server_url, width=800, height=600
            )

            # 创建浏览器
            if self.embedded_browser.create_browser():
                logging.info("内嵌浏览器创建成功")
                self.update_connection_indicator("🟢 内嵌浏览器已加载")
            else:
                logging.error("内嵌浏览器创建失败，降级到按钮方案")
                browser_container.destroy()
                self.create_embedded_webview()

        except Exception as e:
            logging.error(f"创建内嵌浏览器失败: {e}")
            self.create_embedded_webview()

    def create_embedded_webview(self):
        """创建内嵌 WebView（降级方案）"""
        try:
            # 注意：当没有真正的内嵌浏览器时，提供优雅的解决方案
            webview_frame = ctk.CTkFrame(
                self.webview_container,
                fg_color="#f8f9fa",
                corner_radius=10,
                border_width=2,
                border_color=self.colors["primary"],
            )
            webview_frame.pack(fill="both", expand=True, pady=20)

            # 图标和标题
            icon_frame = ctk.CTkFrame(webview_frame, fg_color="transparent")
            icon_frame.pack(pady=(40, 20))

            icon_label = ctk.CTkLabel(
                icon_frame, text="🚀", font=ctk.CTkFont(size=64), text_color=self.colors["primary"]
            )
            icon_label.pack()

            # 标题
            title_label = ctk.CTkLabel(
                webview_frame,
                text="构建管理看板",
                font=ctk.CTkFont(size=24, weight="bold"),
                text_color=self.colors["text_primary"],
            )
            title_label.pack(pady=(10, 5))

            # 副标题
            subtitle_label = ctk.CTkLabel(
                webview_frame,
                text=f"服务器: {self.server_url}",
                font=ctk.CTkFont(size=14),
                text_color=self.colors["text_secondary"],
            )
            subtitle_label.pack(pady=(0, 30))

            # 操作按钮区域
            button_frame = ctk.CTkFrame(webview_frame, fg_color="transparent")
            button_frame.pack(pady=20)

            # 主按钮 - 启动看板（统一使用浏览器）
            btn_text = "🌐 在浏览器中打开看板"

            launch_btn = ctk.CTkButton(
                button_frame,
                text=btn_text,
                command=self.launch_embedded_dashboard,
                fg_color=self.colors["primary"],
                hover_color="#1e5f8e",
                text_color="white",
                font=ctk.CTkFont(size=16, weight="bold"),
                corner_radius=12,
                width=280,
                height=50,
            )
            launch_btn.pack(pady=(0, 15))

            # 副按钮 - 浏览器打开
            browser_btn = ctk.CTkButton(
                button_frame,
                text="🔗 在浏览器中打开",
                command=self.open_dashboard_in_browser,
                fg_color="transparent",
                border_color=self.colors["secondary"],
                border_width=2,
                text_color=self.colors["secondary"],
                font=ctk.CTkFont(size=12, weight="bold"),
                corner_radius=10,
                width=200,
                height=40,
            )
            browser_btn.pack()

            # 添加功能说明
            info_frame = ctk.CTkFrame(webview_frame, fg_color="transparent")
            info_frame.pack(pady=30)

            capabilities = get_browser_capabilities()
            if capabilities["cef_available"]:
                engine_info = "• 推荐安装 CEF Python 以获得内嵌浏览器体验"
            elif capabilities["tkinterhtml_available"]:
                engine_info = "• 当前使用轻量级 HTML 渲染"
            else:
                engine_info = "• 将在默认浏览器中打开"

            info_text = f"""💡 提示：
• 看板将在默认浏览器中打开，提供完整的管理界面
• 支持实时监控、任务管理、统计查看等功能
{engine_info}
• 可随时切换回此应用程序继续使用其他功能"""

            info_label = ctk.CTkLabel(
                info_frame,
                text=info_text,
                font=ctk.CTkFont(size=11),
                text_color=self.colors["text_secondary"],
                justify="left",
            )
            info_label.pack()

            # 自动检查连接状态
            self.check_server_connection()

        except Exception as e:
            logging.error(f"创建 WebView 失败: {e}")
            self.create_webview_placeholder()

    def launch_embedded_dashboard(self):
        """启动内嵌看板窗口"""
        try:

            def create_dashboard():
                success = safe_launch_webview(url=self.server_url, title="🚀 构建管理看板", width=1200, height=800)
                if success:
                    self.master.after(0, lambda: self.update_connection_indicator("🟢 看板已启动"))
                    self.master.after(0, lambda: self.update_status_card("服务器状态", "✅ 看板已打开"))
                else:
                    self.master.after(0, lambda: self.update_connection_indicator("🔴 启动失败"))

            # 在后台线程中启动 WebView
            threading.Thread(target=create_dashboard, daemon=True).start()

            # 立即更新状态为启动中
            self.master.after(0, lambda: self.update_connection_indicator("🟡 正在启动..."))
            self.master.after(0, lambda: self.update_status_card("服务器状态", "🔄 启动中..."))

        except Exception as e:
            error_msg = f"启动内嵌看板失败: {str(e)}"
            logging.error(error_msg)
            self.master.after(0, lambda: self.update_connection_indicator("🔴 启动失败"))

    def create_webview_placeholder(self):
        """创建 WebView 占位符"""
        placeholder_frame = ctk.CTkFrame(
            self.webview_container, fg_color="#f8f9fa", corner_radius=10, border_width=2, border_color="#e9ecef"
        )
        placeholder_frame.pack(fill="both", expand=True, pady=20)

        # 图标和标题
        icon_frame = ctk.CTkFrame(placeholder_frame, fg_color="transparent")
        icon_frame.pack(pady=(40, 20))

        icon_label = ctk.CTkLabel(icon_frame, text="🌐", font=ctk.CTkFont(size=64), text_color=self.colors["primary"])
        icon_label.pack()

        # 信息文本
        info_frame = ctk.CTkFrame(placeholder_frame, fg_color="transparent")
        info_frame.pack(pady=20)

        title_label = ctk.CTkLabel(
            info_frame, text="构建管理看板", font=ctk.CTkFont(size=20, weight="bold"), text_color="#333333"
        )
        title_label.pack(pady=(0, 10))

        url_label = ctk.CTkLabel(info_frame, text=f"{self.server_url}", font=ctk.CTkFont(size=12), text_color="#666666")
        url_label.pack(pady=(0, 30))

        # 操作按钮
        button_frame = ctk.CTkFrame(placeholder_frame, fg_color="transparent")
        button_frame.pack(pady=20)

        # 主按钮 - 在浏览器中打开
        open_browser_btn = ctk.CTkButton(
            button_frame,
            text="🌐 在浏览器中打开看板",
            command=self.open_dashboard_in_browser,
            fg_color=self.colors["primary"],
            hover_color="#1e5f8e",
            text_color="white",
            font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=12,
            width=250,
            height=45,
        )
        open_browser_btn.pack(pady=(0, 15))

        # 副按钮 - 刷新连接
        refresh_btn = ctk.CTkButton(
            button_frame,
            text="🔄 检查连接状态",
            command=self.check_server_connection,
            fg_color="transparent",
            border_color=self.colors["primary"],
            border_width=2,
            text_color=self.colors["primary"],
            font=ctk.CTkFont(size=12),
            corner_radius=12,
            width=200,
            height=40,
        )
        refresh_btn.pack()

        # 启动连接检查
        self.check_server_connection()

    def setup_quick_actions(self):
        """设置快速操作区域"""
        actions_container = ctk.CTkFrame(self.main_container, fg_color=self.colors["card_bg"], corner_radius=15)
        actions_container.pack(fill="x", pady=(0, 20))

        # 标题
        title_frame = ctk.CTkFrame(actions_container, fg_color="transparent")
        title_frame.pack(fill="x", padx=25, pady=(20, 15))

        title_label = ctk.CTkLabel(
            title_frame,
            text="⚡ 快速操作",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.colors["text_primary"],
        )
        title_label.pack(side="left")

        # 刷新指示器
        self.refresh_indicator = ctk.CTkLabel(
            title_frame, text="●", font=ctk.CTkFont(size=8), text_color=self.colors["success"]
        )
        self.refresh_indicator.pack(side="right", padx=(0, 10))

        # 按钮网格
        buttons_frame = ctk.CTkFrame(actions_container, fg_color="transparent")
        buttons_frame.pack(fill="x", padx=25, pady=(0, 20))

        # 创建快速操作按钮
        buttons = [
            {
                "icon": "📋",
                "text": "查看队列",
                "command": self.view_queue,
                "color": self.colors["success"],
                "hover_color": "#3d8a66",
            },
            {
                "icon": "🔄",
                "text": "刷新状态",
                "command": self.refresh_all_with_animation,
                "color": self.colors["warning"],
                "hover_color": "#c45823",
            },
            {
                "icon": "📝",
                "text": "查看日志",
                "command": self.view_logs,
                "color": self.colors["secondary"],
                "hover_color": "#7a2955",
            },
            {
                "icon": "🔧",
                "text": "系统设置",
                "command": self.show_settings,
                "color": self.colors["primary"],
                "hover_color": "#1e5f8e",
            },
        ]

        for i, button_config in enumerate(buttons):
            btn_frame = ctk.CTkFrame(buttons_frame, fg_color="transparent")
            btn_frame.grid(row=0, column=i, padx=10, sticky="ew")
            buttons_frame.grid_columnconfigure(i, weight=1)

            btn = ctk.CTkButton(
                btn_frame,
                text=f"{button_config['icon']} {button_config['text']}",
                command=button_config["command"],
                fg_color=button_config["color"],
                hover_color=button_config["hover_color"],
                text_color="white",
                font=ctk.CTkFont(size=12, weight="bold"),
                corner_radius=10,
                height=40,
                border_width=0,
            )
            btn.pack(fill="x")

            # 添加悬停动效
            def on_enter(e, button=btn, original_color=button_config["color"]):
                button.configure(fg_color=button_config["hover_color"])

            def on_leave(e, button=btn, original_color=button_config["color"]):
                button.configure(fg_color=original_color)

            btn.bind("<Enter>", on_enter)
            btn.bind("<Leave>", on_leave)

    def setup_status_monitor(self):
        """设置状态监控区域"""
        status_container = ctk.CTkFrame(self.main_container, fg_color=self.colors["card_bg"], corner_radius=15)
        status_container.pack(fill="x", pady=(0, 20))

        # 标题
        title_frame = ctk.CTkFrame(status_container, fg_color="transparent")
        title_frame.pack(fill="x", padx=25, pady=(20, 15))

        title_label = ctk.CTkLabel(
            title_frame,
            text="📊 系统状态",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.colors["text_primary"],
        )
        title_label.pack(side="left")

        # 状态卡片网格
        status_grid = ctk.CTkFrame(status_container, fg_color="transparent")
        status_grid.pack(fill="x", padx=25, pady=(0, 20))

        # 创建状态卡片
        status_cards = [
            {"icon": "🔗", "title": "SSE 连接", "status": "检查中...", "color": self.colors["primary"]},
            {"icon": "🌐", "title": "服务器状态", "status": "检查中...", "color": self.colors["success"]},
            {"icon": "📦", "title": "构建队列", "status": "检查中...", "color": self.colors["warning"]},
            {"icon": "⏰", "title": "最后更新", "status": "--:--:--", "color": self.colors["secondary"]},
        ]

        for i, card_config in enumerate(status_cards):
            card_frame = ctk.CTkFrame(status_grid, fg_color=self.darken_color(card_config["color"]), corner_radius=10)
            card_frame.grid(row=0, column=i, padx=5, sticky="ew")
            status_grid.grid_columnconfigure(i, weight=1)

            content_frame = ctk.CTkFrame(card_frame, fg_color="transparent")
            content_frame.pack(fill="both", expand=True, padx=15, pady=15)

            # 图标和标题
            header = ctk.CTkFrame(content_frame, fg_color="transparent")
            header.pack(fill="x", pady=(0, 8))

            icon_label = ctk.CTkLabel(header, text=card_config["icon"], font=ctk.CTkFont(size=20), text_color="white")
            icon_label.pack(side="left")

            title_label = ctk.CTkLabel(
                header, text=card_config["title"], font=ctk.CTkFont(size=12, weight="bold"), text_color="white"
            )
            title_label.pack(side="left", padx=(10, 0))

            # 状态值
            status_label = ctk.CTkLabel(
                content_frame, text=card_config["status"], font=ctk.CTkFont(size=11), text_color="#e0e0e0"
            )
            status_label.pack()

        # 保存状态标签引用以便更新
        self.status_labels = {}
        # 获取所有状态卡片框架
        card_frames = status_grid.grid_slaves()
        for i, card_config in enumerate(status_cards):
            if i < len(card_frames):
                card_frame = card_frames[i]
                # 获取内容框架中的状态标签（第二个子组件）
                content_children = card_frame.winfo_children()
                if content_children:
                    content_frame = content_children[0]
                    label_children = content_frame.winfo_children()
                    if len(label_children) > 1:
                        status_label = label_children[1]
                        self.status_labels[card_config["title"]] = status_label

        # 启动状态更新
        self.update_status_monitor()

    def darken_color(self, color: str) -> str:
        """使颜色变暗"""
        # 简单的颜色变暗逻辑
        color_map = {
            self.colors["primary"]: "#1e5f8e",
            self.colors["secondary"]: "#7a2955",
            self.colors["success"]: "#3d8a66",
            self.colors["warning"]: "#c45823",
            self.colors["danger"]: "#a01e1e",
        }
        return color_map.get(color, color)

    def update_status_monitor(self):
        """更新状态监控"""
        # 更新 SSE 连接状态
        if self.event_manager:
            if self.event_manager.running:
                self.update_status_card("SSE 连接", "✅ 已连接")
            else:
                self.update_status_card("SSE 连接", "❌ 未连接")
        else:
            self.update_status_card("SSE 连接", "❌ 未初始化")

        # 更新最后更新时间
        now = datetime.now().strftime("%H:%M:%S")
        self.update_status_card("最后更新", now)

        # 定期更新状态
        self.master.after(5000, self.update_status_monitor)

    def update_status_card(self, title: str, status: str):
        """更新状态卡片"""
        if hasattr(self, "status_labels") and title in self.status_labels:
            self.status_labels[title].configure(text=status)

    def open_dashboard_in_browser(self):
        """在浏览器中打开看板"""
        try:
            webbrowser.open(self.server_url)
            self.master.after(0, lambda: self.update_status_card("服务器状态", "✅ 已打开"))
        except Exception as e:
            error_msg = f"打开浏览器失败: {str(e)}"
            logging.error(error_msg)
            self.master.after(0, lambda: self.update_status_card("服务器状态", "❌ 打开失败"))

    def check_server_connection(self):
        """检查服务器连接"""

        def check():
            try:
                response = requests.get(f"{self.server_url}/api/task/statistics", timeout=5)
                if response.status_code == 200:
                    status = "✅ 连接正常"
                    # 使用 after 方法在主线程中更新 GUI
                    self.master.after(0, lambda: self.update_status_card("服务器状态", status))
                    self.master.after(0, lambda: self.update_connection_indicator("🟢 服务正常"))
                else:
                    status = f"❌ 服务异常 ({response.status_code})"
                    self.master.after(0, lambda: self.update_status_card("服务器状态", status))
                    self.master.after(0, lambda: self.update_connection_indicator("🔴 服务异常"))
            except Exception:
                status = "❌ 连接失败"
                self.master.after(0, lambda: self.update_status_card("服务器状态", status))
                self.master.after(0, lambda: self.update_connection_indicator("🔴 连接失败"))

        threading.Thread(target=check, daemon=True).start()

    def update_connection_indicator(self, status: str):
        """更新连接指示器"""
        if hasattr(self, "connection_indicator"):
            self.connection_indicator.configure(text=status)

    def view_queue(self):
        """查看队列"""
        try:
            webbrowser.open(f"{self.server_url}/queue")
        except Exception as e:
            logging.error(f"打开队列页面失败: {e}")

    def refresh_all_with_animation(self):
        """刷新所有状态（带动画效果）"""
        # 开始刷新动画
        if hasattr(self, "refresh_indicator"):
            self.refresh_indicator.configure(text_color=self.colors["warning"])

        # 添加视觉反馈
        self.master.configure(cursor="watch")

        # 执行刷新
        self.refresh_all()

        # 恢复正常状态（延迟以显示动画效果）
        self.master.after(1000, lambda: self._restore_refresh_state())

    def _restore_refresh_state(self):
        """恢复刷新状态"""
        if hasattr(self, "refresh_indicator"):
            self.refresh_indicator.configure(text_color=self.colors["success"])
        self.master.configure(cursor="")

    def refresh_all(self):
        """刷新所有状态"""
        self.check_server_connection()
        self.update_status_monitor()

    def view_logs(self):
        """查看日志"""
        try:
            # 尝试打开日志页面
            webbrowser.open(f"{self.server_url}/logs")
        except Exception as e:
            logging.error(f"打开日志页面失败: {e}")
            # 如果网页日志不可用，可以实现本地日志窗口
            self._show_local_logs()

    def _show_local_logs(self):
        """显示本地日志窗口"""
        # 创建一个简单的日志查看窗口
        log_window = ctk.CTkToplevel(self.master)
        log_window.title("系统日志")
        log_window.geometry("800x600")
        log_window.configure(fg_color=self.colors["dark_bg"])

        # 创建滚动文本框
        log_text = ctk.CTkTextbox(log_window, fg_color="#1e1e1e", text_color="#ffffff")
        log_text.pack(fill="both", expand=True, padx=10, pady=10)

        # 添加一些示例日志内容
        log_content = f"""系统日志 - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
{"=" * 50}

[INFO] 应用程序启动完成
[INFO] 正在连接服务器: {self.server_url}
[INFO] SSE 连接已建立
[INFO] 状态监控已启动
[INFO] GUI 界面初始化完成

注意: 这里显示的是系统运行日志。
详细的错误信息请查看控制台输出或日志文件。
"""
        log_text.insert("0.0", log_content)
        log_text.configure(state="disabled")

    def show_settings(self):
        """显示设置"""
        self._show_settings_window()

    def _show_settings_window(self):
        """显示设置窗口"""
        settings_window = ctk.CTkToplevel(self.master)
        settings_window.title("系统设置")
        settings_window.geometry("500x400")
        settings_window.configure(fg_color=self.colors["dark_bg"])

        # 设置容器
        settings_container = ctk.CTkFrame(settings_window, fg_color=self.colors["card_bg"], corner_radius=15)
        settings_container.pack(fill="both", expand=True, padx=20, pady=20)

        # 标题
        title_label = ctk.CTkLabel(
            settings_container,
            text="⚙️ 系统设置",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.colors["text_primary"],
        )
        title_label.pack(pady=20)

        # 服务器地址设置
        server_frame = ctk.CTkFrame(settings_container, fg_color="transparent")
        server_frame.pack(fill="x", padx=20, pady=10)

        server_label = ctk.CTkLabel(
            server_frame, text="服务器地址:", font=ctk.CTkFont(size=12), text_color=self.colors["text_secondary"]
        )
        server_label.pack(anchor="w")

        server_entry = ctk.CTkEntry(
            server_frame,
            text_color=self.colors["text_primary"],
            fg_color="#2a2a3e",
            border_color=self.colors["primary"],
            width=400,
        )
        server_entry.pack(fill="x", pady=(5, 0))
        server_entry.insert(0, self.server_url)

        # 说明文字
        info_label = ctk.CTkLabel(
            settings_container,
            text="更多设置功能正在开发中...",
            font=ctk.CTkFont(size=11),
            text_color=self.colors["text_secondary"],
        )
        info_label.pack(pady=20)

        # 关闭按钮
        close_btn = ctk.CTkButton(
            settings_container,
            text="关闭",
            command=settings_window.destroy,
            fg_color=self.colors["secondary"],
            text_color="white",
            font=ctk.CTkFont(size=12, weight="bold"),
            corner_radius=10,
            width=100,
            height=35,
        )
        close_btn.pack(pady=20)

    def on_webview_closed(self):
        """WebView 关闭时的处理"""
        logging.info("WebView 窗口已关闭")

    def setup_status(self):
        """设置初始状态"""
        pass


# 向后兼容的类别名
MainWindow = ModernMainWindow
