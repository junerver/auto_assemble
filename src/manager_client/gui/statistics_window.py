"""
Statistics Window Module

This module provides the modern statistics popup window for the manager client.
"""

import logging
import threading
from typing import Optional, Dict, List, Any

try:
    import customtkinter as ctk
except ImportError:
    ctk = None

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None

import requests
from datetime import datetime


class ModernStatisticsWindow:
    """现代化统计窗口类"""

    def __init__(self, parent, server_url: str):
        self.parent = parent
        self.server_url = server_url
        self.window: Optional[ctk.CTkToplevel] = None
        self.loading = False

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
            "chart_bg": "#0f3460",  # 图表背景
        }

        self.create_window()
        self.load_statistics()

    def create_window(self):
        """创建现代化统计窗口"""
        self.window = ctk.CTkToplevel(self.parent)
        self.window.title("📊 构建统计分析")
        self.window.geometry("1000x700")
        self.window.transient(self.parent)
        self.window.grab_set()

        # 设置窗口样式
        self.window.configure(fg_color=self.colors["dark_bg"])

        # 设置窗口关闭行为
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)

        # 主容器
        self.main_frame = ctk.CTkFrame(self.window, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True, padx=15, pady=15)

        # 顶部工具栏
        self.setup_toolbar()

        # 内容区域
        self.setup_content_area()

        # 底部状态栏
        self.setup_status_bar()

        # 居中显示窗口
        self.center_window()

    def setup_toolbar(self):
        """设置现代化工具栏"""
        toolbar_frame = ctk.CTkFrame(
            self.main_frame,
            fg_color=self.colors["card_bg"],
            corner_radius=12,
            border_width=1,
            border_color=self.colors["primary"],
        )
        toolbar_frame.pack(fill="x", pady=(0, 15))

        # 标题区域
        title_frame = ctk.CTkFrame(toolbar_frame, fg_color="transparent")
        title_frame.pack(fill="x", padx=20, pady=15)

        # 主标题
        title_label = ctk.CTkLabel(
            title_frame,
            text="📊 构建统计分析",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=self.colors["text_primary"],
        )
        title_label.pack(side="left")

        # 服务器信息
        server_label = ctk.CTkLabel(
            title_frame,
            text=f"📡 {self.server_url}",
            font=ctk.CTkFont(size=12),
            text_color=self.colors["text_secondary"],
        )
        server_label.pack(side="left", padx=(30, 0))

        # 右侧操作按钮
        actions_frame = ctk.CTkFrame(title_frame, fg_color="transparent")
        actions_frame.pack(side="right")

        # 刷新按钮
        refresh_btn = ctk.CTkButton(
            actions_frame,
            text="🔄 刷新",
            command=self.load_statistics,
            fg_color=self.colors["success"],
            hover_color="#3d8a66",
            text_color="white",
            font=ctk.CTkFont(size=11, weight="bold"),
            corner_radius=8,
            width=80,
            height=32,
        )
        refresh_btn.pack(side="right", padx=(10, 0))

        # 导出按钮
        export_btn = ctk.CTkButton(
            actions_frame,
            text="📄 导出",
            command=self.export_data,
            fg_color=self.colors["secondary"],
            hover_color="#7a2955",
            text_color="white",
            font=ctk.CTkFont(size=11, weight="bold"),
            corner_radius=8,
            width=80,
            height=32,
        )
        export_btn.pack(side="right")

    def setup_content_area(self):
        """设置内容区域"""
        content_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        content_frame.pack(fill="both", expand=True)

        # 创建标签页
        self.tabview = ctk.CTkTabview(
            content_frame,
            fg_color="transparent",
            segmented_button_fg_color=self.colors["card_bg"],
            segmented_button_selected_color=self.colors["primary"],
            text_color=self.colors["text_primary"],
        )
        self.tabview.pack(fill="both", expand=True)

        # 设置标签页样式
        self.tabview._segmented_button.grid(padx=10, pady=10)

        # 概览标签页
        self.overview_tab = self.tabview.add("📋 概览")
        self.setup_overview_tab()

        # 项目统计标签页
        self.projects_tab = self.tabview.add("📈 项目统计")
        self.setup_projects_tab()

        # 用户统计标签页
        self.users_tab = self.tabview.add("👥 用户统计")
        self.setup_users_tab()

    def setup_overview_tab(self):
        """设置概览标签页"""
        # 创建滚动容器
        scroll_frame = ctk.CTkScrollableFrame(self.overview_tab, fg_color="transparent", corner_radius=0)
        scroll_frame.pack(fill="both", expand=True, padx=15, pady=15)

        # 概述卡片
        overview_frame = ctk.CTkFrame(scroll_frame, fg_color=self.colors["card_bg"], corner_radius=15)
        overview_frame.pack(fill="x", pady=(0, 20))

        # 标题
        title_frame = ctk.CTkFrame(overview_frame, fg_color="transparent")
        title_frame.pack(fill="x", padx=25, pady=(20, 15))

        title_label = ctk.CTkLabel(
            title_frame,
            text="📊 数据概览",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.colors["text_primary"],
        )
        title_label.pack(side="left")

        # 最后更新时间
        self.overview_update_time = ctk.CTkLabel(
            title_frame, text="更新中...", font=ctk.CTkFont(size=11), text_color=self.colors["text_secondary"]
        )
        self.overview_update_time.pack(side="right")

        # 统计卡片网格 - 保存引用
        self.overview_cards_frame = ctk.CTkFrame(overview_frame, fg_color="transparent")
        self.overview_cards_frame.pack(fill="x", padx=25, pady=(0, 25))

        # 2x2 网格布局
        for i in range(2):
            self.overview_cards_frame.grid_rowconfigure(i, weight=1)
        for i in range(2):
            self.overview_cards_frame.grid_columnconfigure(i, weight=1)

        # 显示初始加载状态
        self.create_overview_loading_state()

    def create_overview_loading_state(self):
        """创建概览加载状态"""
        # 显示加载提示
        loading_label = ctk.CTkLabel(
            self.overview_cards_frame,
            text="🔄 正在加载统计数据...",
            font=ctk.CTkFont(size=16),
            text_color=self.colors["text_secondary"],
        )
        loading_label.grid(row=0, column=0, columnspan=2, pady=50)
        self.overview_loading_label = loading_label

    def setup_projects_tab(self):
        """设置项目统计标签页"""
        # 创建滚动容器
        scroll_frame = ctk.CTkScrollableFrame(self.projects_tab, fg_color="transparent", corner_radius=0)
        scroll_frame.pack(fill="both", expand=True, padx=15, pady=15)

        # 项目统计框架
        projects_frame = ctk.CTkFrame(scroll_frame, fg_color=self.colors["card_bg"], corner_radius=15)
        projects_frame.pack(fill="both", expand=True, pady=(0, 20))

        # 标题
        title_frame = ctk.CTkFrame(projects_frame, fg_color="transparent")
        title_frame.pack(fill="x", padx=25, pady=(20, 15))

        title_label = ctk.CTkLabel(
            title_frame,
            text="📈 项目构建统计",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.colors["text_primary"],
        )
        title_label.pack(side="left")

        # 数据将在此处动态添加
        self.projects_container = ctk.CTkFrame(projects_frame, fg_color="transparent")
        self.projects_container.pack(fill="both", expand=True, padx=25, pady=(0, 25))

        # 显示加载中
        self.show_projects_loading()

    def setup_users_tab(self):
        """设置用户统计标签页"""
        # 创建滚动容器
        scroll_frame = ctk.CTkScrollableFrame(self.users_tab, fg_color="transparent", corner_radius=0)
        scroll_frame.pack(fill="both", expand=True, padx=15, pady=15)

        # 用户统计框架
        users_frame = ctk.CTkFrame(scroll_frame, fg_color=self.colors["card_bg"], corner_radius=15)
        users_frame.pack(fill="both", expand=True, pady=(0, 20))

        # 标题
        title_frame = ctk.CTkFrame(users_frame, fg_color="transparent")
        title_frame.pack(fill="x", padx=25, pady=(20, 15))

        title_label = ctk.CTkLabel(
            title_frame,
            text="👥 用户使用统计",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.colors["text_primary"],
        )
        title_label.pack(side="left")

        # 数据将在此处动态添加
        self.users_container = ctk.CTkFrame(users_frame, fg_color="transparent")
        self.users_container.pack(fill="both", expand=True, padx=25, pady=(0, 25))

        # 显示加载中
        self.show_users_loading()

    def setup_status_bar(self):
        """设置状态栏"""
        status_frame = ctk.CTkFrame(self.main_frame, fg_color=self.colors["card_bg"], corner_radius=12)
        status_frame.pack(fill="x", pady=(15, 0))

        # 状态内容
        content_frame = ctk.CTkFrame(status_frame, fg_color="transparent")
        content_frame.pack(fill="x", padx=20, pady=12)

        # 状态指示器
        self.status_indicator = ctk.CTkLabel(
            content_frame, text="🔄 准备就绪", font=ctk.CTkFont(size=11), text_color=self.colors["text_secondary"]
        )
        self.status_indicator.pack(side="left")

        # 更新时间
        self.update_time_label = ctk.CTkLabel(
            content_frame, text="更新: --", font=ctk.CTkFont(size=10), text_color=self.colors["text_secondary"]
        )
        self.update_time_label.pack(side="right")

    def show_projects_loading(self):
        """显示项目统计加载状态"""
        if hasattr(self, "projects_container"):
            # 清空现有内容
            for widget in self.projects_container.winfo_children():
                widget.destroy()

            # 加载提示
            loading_frame = ctk.CTkFrame(self.projects_container, fg_color=self.colors["chart_bg"], corner_radius=12)
            loading_frame.pack(fill="both", expand=True, pady=50)

            loading_label = ctk.CTkLabel(
                loading_frame,
                text="🔄 正在加载项目统计数据...",
                font=ctk.CTkFont(size=14),
                text_color=self.colors["text_secondary"],
            )
            loading_label.pack()

    def show_users_loading(self):
        """显示用户统计加载状态"""
        if hasattr(self, "users_container"):
            # 清空现有内容
            for widget in self.users_container.winfo_children():
                widget.destroy()

            # 加载提示
            loading_frame = ctk.CTkFrame(self.users_container, fg_color=self.colors["chart_bg"], corner_radius=12)
            loading_frame.pack(fill="both", expand=True, pady=50)

            loading_label = ctk.CTkLabel(
                loading_frame,
                text="🔄 正在加载用户统计数据...",
                font=ctk.CTkFont(size=14),
                text_color=self.colors["text_secondary"],
            )
            loading_label.pack()

    def create_overview_card(
        self, parent, row: int, col: int, icon: str, title: str, value: str, description: str, color: str
    ):
        """创建概览统计卡片"""
        card = ctk.CTkFrame(parent, fg_color=color, corner_radius=15)
        card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

        # 卡片内容
        content_frame = ctk.CTkFrame(card, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # 顶部图标和数值
        top_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        top_frame.pack(fill="x", pady=(0, 15))

        icon_label = ctk.CTkLabel(top_frame, text=icon, font=ctk.CTkFont(size=32), text_color="white")
        icon_label.pack(side="left")

        value_label = ctk.CTkLabel(top_frame, text=value, font=ctk.CTkFont(size=28, weight="bold"), text_color="white")
        value_label.pack(side="right")

        # 分隔线
        separator = ctk.CTkFrame(content_frame, fg_color="white", height=1)
        separator.pack(fill="x", pady=(5, 10))

        # 标题
        title_label = ctk.CTkLabel(
            content_frame, text=title, font=ctk.CTkFont(size=14, weight="bold"), text_color="white"
        )
        title_label.pack(pady=(0, 5))

        # 描述
        desc_label = ctk.CTkLabel(content_frame, text=description, font=ctk.CTkFont(size=11), text_color="#e0e0e0")
        desc_label.pack()

        return card

    def display_overview(self, tasks_stats: List[Dict[str, Any]], packer_usage: List[Dict[str, Any]]):
        """显示概览数据"""
        try:
            # 计算概览数据
            total_projects = len(tasks_stats)
            total_builds = sum([task.get("count", 0) for task in tasks_stats])
            total_users = len(packer_usage)
            total_user_builds = sum([user.get("count", 0) for user in packer_usage])

            # 清空现有内容
            for widget in self.overview_cards_frame.winfo_children():
                widget.destroy()

            # 创建统计卡片
            self.create_overview_card(
                self.overview_cards_frame,
                0,
                0,
                "📈",
                "项目总数",
                str(total_projects),
                "当前活跃的项目数量",
                self.colors["primary"],
            )
            self.create_overview_card(
                self.overview_cards_frame,
                0,
                1,
                "🔨",
                "总构建次数",
                str(total_builds),
                "所有项目的构建总次数",
                self.colors["success"],
            )
            self.create_overview_card(
                self.overview_cards_frame,
                1,
                0,
                "👥",
                "用户总数",
                str(total_users),
                "使用系统的用户数量",
                self.colors["secondary"],
            )
            self.create_overview_card(
                self.overview_cards_frame,
                1,
                1,
                "📊",
                "用户构建",
                str(total_user_builds),
                "用户发起的构建次数",
                self.colors["warning"],
            )

            logging.info(f"概览数据显示完成: 项目数={total_projects}, 构建次数={total_builds}, 用户数={total_users}")

        except Exception as e:
            logging.error(f"显示概览失败: {e}")
            # 显示错误状态
            for widget in self.overview_cards_frame.winfo_children():
                widget.destroy()
            error_label = ctk.CTkLabel(
                self.overview_cards_frame,
                text=f"❌ 加载失败: {str(e)}",
                font=ctk.CTkFont(size=14),
                text_color=self.colors["danger"],
            )
            error_label.grid(row=0, column=0, columnspan=2, pady=50)

    def display_projects_statistics(self, tasks_stats: List[Dict[str, Any]]):
        """显示项目统计"""
        if not hasattr(self, "projects_container"):
            return

        # 清空现有内容
        for widget in self.projects_container.winfo_children():
            widget.destroy()

        if not tasks_stats:
            # 无数据提示
            no_data_frame = ctk.CTkFrame(self.projects_container, fg_color=self.colors["chart_bg"], corner_radius=12)
            no_data_frame.pack(fill="both", expand=True, pady=50)

            no_data_label = ctk.CTkLabel(
                no_data_frame,
                text="📭 暂无项目统计数据",
                font=ctk.CTkFont(size=14),
                text_color=self.colors["text_secondary"],
            )
            no_data_label.pack()
            return

        # 按构建次数排序
        sorted_tasks = sorted(tasks_stats, key=lambda x: x.get("count", 0), reverse=True)
        max_count = max([task.get("count", 0) for task in sorted_tasks]) if sorted_tasks else 1

        # 创建统计列表
        for i, task in enumerate(sorted_tasks):
            item_frame = ctk.CTkFrame(self.projects_container, fg_color=self.colors["chart_bg"], corner_radius=12)
            item_frame.pack(fill="x", pady=(0, 10))

            content_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
            content_frame.pack(fill="x", padx=20, pady=15)

            # 排名和项目名
            info_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
            info_frame.pack(fill="x", pady=(0, 10))

            # 排名标签
            rank_text = f"#{i + 1}"
            if i < 3:  # 前三名使用特殊样式
                rank_label = ctk.CTkLabel(
                    info_frame,
                    text=rank_text,
                    font=ctk.CTkFont(size=14, weight="bold"),
                    text_color=self.colors["warning"]
                    if i == 0
                    else self.colors["success"]
                    if i == 1
                    else self.colors["primary"],
                )
            else:
                rank_label = ctk.CTkLabel(
                    info_frame,
                    text=rank_text,
                    font=ctk.CTkFont(size=12, weight="bold"),
                    text_color=self.colors["text_secondary"],
                )
            rank_label.pack(side="left", padx=(0, 10))

            # 项目名
            name_label = ctk.CTkLabel(
                info_frame,
                text=task.get("prod_name", "未知项目"),
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=self.colors["text_primary"],
            )
            name_label.pack(side="left", padx=(15, 0))

            # 统计信息
            stats_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
            stats_frame.pack(fill="x")

            # 构建次数
            count = task.get("count", 0)
            count_label = ctk.CTkLabel(
                stats_frame,
                text=f"构建次数: {count}",
                font=ctk.CTkFont(size=11),
                text_color=self.colors["text_secondary"],
            )
            count_label.pack(side="left")

            # 进度条
            progress_value = (count / max_count) if max_count > 0 else 0
            progress_bar = ctk.CTkProgressBar(stats_frame, progress_color=self.colors["primary"], width=200)
            progress_bar.set(progress_value)
            progress_bar.pack(side="left", padx=(20, 10))

            # 百分比
            total_count = sum([t.get("count", 0) for t in sorted_tasks])
            percentage = (count / total_count) * 100 if total_count > 0 else 0
            percentage_label = ctk.CTkLabel(
                stats_frame,
                text=f"{percentage:.1f}%",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=self.colors["primary"],
            )
            percentage_label.pack(side="right")

    def display_users_statistics(self, packer_usage: List[Dict[str, Any]]):
        """显示用户统计"""
        if not hasattr(self, "users_container"):
            return

        # 清空现有内容
        for widget in self.users_container.winfo_children():
            widget.destroy()

        if not packer_usage:
            # 无数据提示
            no_data_frame = ctk.CTkFrame(self.users_container, fg_color=self.colors["chart_bg"], corner_radius=12)
            no_data_frame.pack(fill="both", expand=True, pady=50)

            no_data_label = ctk.CTkLabel(
                no_data_frame,
                text="📭 暂无用户统计数据",
                font=ctk.CTkFont(size=14),
                text_color=self.colors["text_secondary"],
            )
            no_data_label.pack()
            return

        # 按使用次数排序
        sorted_users = sorted(packer_usage, key=lambda x: x.get("count", 0), reverse=True)
        max_count = max([user.get("count", 0) for user in sorted_users]) if sorted_users else 1

        # 创建统计列表
        for i, user in enumerate(sorted_users):
            item_frame = ctk.CTkFrame(self.users_container, fg_color=self.colors["chart_bg"], corner_radius=12)
            item_frame.pack(fill="x", pady=(0, 10))

            content_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
            content_frame.pack(fill="x", padx=20, pady=15)

            # 排名和用户名
            info_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
            info_frame.pack(fill="x", pady=(0, 10))

            # 排名标签
            rank_text = f"#{i + 1}"
            if i < 3:  # 前三名使用特殊样式
                rank_label = ctk.CTkLabel(
                    info_frame,
                    text=rank_text,
                    font=ctk.CTkFont(size=14, weight="bold"),
                    text_color=self.colors["warning"]
                    if i == 0
                    else self.colors["success"]
                    if i == 1
                    else self.colors["secondary"],
                )
            else:
                rank_label = ctk.CTkLabel(
                    info_frame,
                    text=rank_text,
                    font=ctk.CTkFont(size=12, weight="bold"),
                    text_color=self.colors["text_secondary"],
                )
            rank_label.pack(side="left", padx=(0, 10))

            # 用户名
            name_label = ctk.CTkLabel(
                info_frame,
                text=user.get("author", "未知用户"),
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=self.colors["text_primary"],
            )
            name_label.pack(side="left", padx=(15, 0))

            # 统计信息
            stats_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
            stats_frame.pack(fill="x")

            # 使用次数
            count = user.get("count", 0)
            count_label = ctk.CTkLabel(
                stats_frame,
                text=f"使用次数: {count}",
                font=ctk.CTkFont(size=11),
                text_color=self.colors["text_secondary"],
            )
            count_label.pack(side="left")

            # 进度条
            progress_value = (count / max_count) if max_count > 0 else 0
            progress_bar = ctk.CTkProgressBar(stats_frame, progress_color=self.colors["secondary"], width=200)
            progress_bar.set(progress_value)
            progress_bar.pack(side="left", padx=(20, 10))

            # 百分比
            total_count = sum([u.get("count", 0) for u in sorted_users])
            percentage = (count / total_count) * 100 if total_count > 0 else 0
            percentage_label = ctk.CTkLabel(
                stats_frame,
                text=f"{percentage:.1f}%",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=self.colors["secondary"],
            )
            percentage_label.pack(side="right")

    def load_statistics(self):
        """加载统计数据"""
        if self.loading:
            return

        self.loading = True
        self.update_status("正在加载统计数据...")

        def load():
            try:
                # 获取统计数据
                response = requests.get(f"{self.server_url}/api/task/statistics", timeout=10)

                if response.status_code == 200:
                    data = response.json()
                    self.window.after(0, lambda: self.display_statistics(data))
                else:
                    self.window.after(0, lambda: self.show_error(f"获取统计数据失败: {response.status_code}"))

            except Exception as e:
                error_msg = f"网络错误: {str(e)}"
                self.window.after(0, lambda: self.show_error(error_msg))
            finally:
                self.loading = False

        # 在后台线程中加载
        threading.Thread(target=load, daemon=True).start()

    def display_statistics(self, data: Dict[str, Any]):
        """显示统计数据"""
        try:
            # 解析数据
            tasks_stats = data.get("tasks", [])
            packer_usage = data.get("packer_usage", [])

            # 更新各个标签页
            self.display_overview(tasks_stats, packer_usage)
            self.display_projects_statistics(tasks_stats)
            self.display_users_statistics(packer_usage)

            # 更新状态
            self.update_status("统计数据加载完成")

            # 更新时间
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if hasattr(self, "update_time_label"):
                self.update_time_label.configure(text=f"更新: {now}")
            if hasattr(self, "overview_update_time"):
                self.overview_update_time.configure(text=now)

        except Exception as e:
            logging.error(f"显示统计数据时发生错误: {e}")
            self.show_error(f"显示数据时发生错误: {str(e)}")

    def show_error(self, message: str):
        """显示错误信息"""
        self.update_status(f"❌ {message}")

        # 在所有标签页显示错误
        containers = [self.projects_container, self.users_container]

        for container in containers:
            if hasattr(container, "winfo_children"):
                for widget in container.winfo_children():
                    widget.destroy()

                error_frame = ctk.CTkFrame(container, fg_color=self.colors["danger"], corner_radius=12)
                error_frame.pack(fill="both", expand=True, pady=50)

                error_label = ctk.CTkLabel(
                    error_frame, text=f"❌ {message}", font=ctk.CTkFont(size=14), text_color="white"
                )
                error_label.pack()

    def update_status(self, message: str):
        """更新状态"""
        if hasattr(self, "status_indicator"):
            self.status_indicator.configure(text=message)

    def export_data(self):
        """导出数据"""
        # TODO: 实现数据导出功能
        self.update_status("导出功能开发中...")

    def center_window(self):
        """居中显示窗口"""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"{width}x{height}+{x}+{y}")

    def on_closing(self):
        """关闭窗口"""
        if self.window:
            self.window.destroy()


# 向后兼容的类别名
StatisticsWindow = ModernStatisticsWindow
