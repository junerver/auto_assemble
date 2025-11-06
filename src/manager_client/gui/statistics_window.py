"""
Statistics Window Module

This module provides the statistics popup window for the manager client.
"""

import logging
import threading
from typing import Optional, Dict, List, Any

try:
    import customtkinter as ctk
except ImportError:
    ctk = None

try:
    from PIL import Image
except ImportError:
    Image = None

import requests
from datetime import datetime


class StatisticsWindow:
    """统计窗口类"""

    def __init__(self, parent, server_url: str):
        self.parent = parent
        self.server_url = server_url
        self.window: Optional[ctk.CTkToplevel] = None
        self.loading = False

        self.create_window()
        self.load_statistics()

    def create_window(self):
        """创建统计窗口"""
        self.window = ctk.CTkToplevel(self.parent)
        self.window.title("📊 构建统计")
        self.window.geometry("800x600")
        self.window.transient(self.parent)
        self.window.grab_set()

        # 设置窗口关闭行为
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)

        # 主框架
        self.main_frame = ctk.CTkFrame(self.window)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # 顶部工具栏
        self.setup_toolbar()

        # 内容区域
        self.setup_content_area()

        # 底部状态栏
        self.setup_status_bar()

        # 居中显示窗口
        self.center_window()

    def setup_toolbar(self):
        """设置工具栏"""
        toolbar_frame = ctk.CTkFrame(self.main_frame)
        toolbar_frame.pack(fill="x", padx=5, pady=5)

        # 标题
        title_label = ctk.CTkLabel(toolbar_frame, text="📊 构建统计信息", font=ctk.CTkFont(size=16, weight="bold"))
        title_label.pack(side="left", padx=10)

        # 刷新按钮
        refresh_btn = ctk.CTkButton(toolbar_frame, text="🔄 刷新数据", command=self.load_statistics, width=100)
        refresh_btn.pack(side="right", padx=5)

        # 导出按钮
        export_btn = ctk.CTkButton(toolbar_frame, text="📄 导出数据", command=self.export_data, width=100)
        export_btn.pack(side="right", padx=5)

    def setup_content_area(self):
        """设置内容区域"""
        content_frame = ctk.CTkFrame(self.main_frame)
        content_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # 创建标签页
        self.tabview = ctk.CTkTabview(content_frame)
        self.tabview.pack(fill="both", expand=True)

        # 项目统计标签页
        self.projects_tab = self.tabview.add("📈 项目统计")
        self.setup_projects_tab()

        # 用户统计标签页
        self.users_tab = self.tabview.add("👥 用户统计")
        self.setup_users_tab()

        # 概览标签页
        self.overview_tab = self.tabview.add("📋 概览")
        self.setup_overview_tab()

    def setup_projects_tab(self):
        """设置项目统计标签页"""
        # 创建滚动框架
        self.projects_scroll_frame = ctk.CTkScrollableFrame(self.projects_tab)
        self.projects_scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # 项目统计标题
        title_frame = ctk.CTkFrame(self.projects_scroll_frame)
        title_frame.pack(fill="x", pady=10)

        title_label = ctk.CTkLabel(title_frame, text="各项目构建次数统计", font=ctk.CTkFont(size=14, weight="bold"))
        title_label.pack(pady=10)

        # 数据将在此处动态添加
        self.projects_data_frame = ctk.CTkFrame(self.projects_scroll_frame)
        self.projects_data_frame.pack(fill="both", expand=True, pady=10)

        # 显示加载中
        self.show_projects_loading()

    def setup_users_tab(self):
        """设置用户统计标签页"""
        # 创建滚动框架
        self.users_scroll_frame = ctk.CTkScrollableFrame(self.users_tab)
        self.users_scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # 用户统计标题
        title_frame = ctk.CTkFrame(self.users_scroll_frame)
        title_frame.pack(fill="x", pady=10)

        title_label = ctk.CTkLabel(title_frame, text="用户使用次数统计", font=ctk.CTkFont(size=14, weight="bold"))
        title_label.pack(pady=10)

        # 数据将在此处动态添加
        self.users_data_frame = ctk.CTkFrame(self.users_scroll_frame)
        self.users_data_frame.pack(fill="both", expand=True, pady=10)

        # 显示加载中
        self.show_users_loading()

    def setup_overview_tab(self):
        """设置概览标签页"""
        overview_frame = ctk.CTkFrame(self.overview_tab)
        overview_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # 概览标题
        title_label = ctk.CTkLabel(overview_frame, text="📋 统计概览", font=ctk.CTkFont(size=14, weight="bold"))
        title_label.pack(pady=10)

        # 统计卡片
        self.stats_cards_frame = ctk.CTkFrame(overview_frame)
        self.stats_cards_frame.pack(fill="x", pady=10)

        # 显示加载中
        self.show_overview_loading()

    def setup_status_bar(self):
        """设置状态栏"""
        status_frame = ctk.CTkFrame(self.main_frame)
        status_frame.pack(fill="x", padx=5, pady=5)

        self.status_label = ctk.CTkLabel(status_frame, text="准备就绪", font=ctk.CTkFont(size=11))
        self.status_label.pack(side="left", padx=10)

        # 最后更新时间
        self.update_time_label = ctk.CTkLabel(status_frame, text="最后更新: --", font=ctk.CTkFont(size=10))
        self.update_time_label.pack(side="right", padx=10)

    def show_projects_loading(self):
        """显示项目统计加载状态"""
        if hasattr(self, "projects_data_frame"):
            # 清空现有内容
            for widget in self.projects_data_frame.winfo_children():
                widget.destroy()

            loading_label = ctk.CTkLabel(
                self.projects_data_frame, text="🔄 正在加载项目统计数据...", font=ctk.CTkFont(size=12)
            )
            loading_label.pack(pady=50)

    def show_users_loading(self):
        """显示用户统计加载状态"""
        if hasattr(self, "users_data_frame"):
            # 清空现有内容
            for widget in self.users_data_frame.winfo_children():
                widget.destroy()

            loading_label = ctk.CTkLabel(
                self.users_data_frame, text="🔄 正在加载用户统计数据...", font=ctk.CTkFont(size=12)
            )
            loading_label.pack(pady=50)

    def show_overview_loading(self):
        """显示概览加载状态"""
        if hasattr(self, "stats_cards_frame"):
            # 清空现有内容
            for widget in self.stats_cards_frame.winfo_children():
                widget.destroy()

            loading_label = ctk.CTkLabel(
                self.stats_cards_frame, text="🔄 正在加载统计概览...", font=ctk.CTkFont(size=12)
            )
            loading_label.pack(pady=50)

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

            except Exception:
                self.window.after(0, lambda: self.show_error("网络错误: 请检查连接"))
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

            # 更新项目统计
            self.display_projects_statistics(tasks_stats)

            # 更新用户统计
            self.display_users_statistics(packer_usage)

            # 更新概览
            self.display_overview(tasks_stats, packer_usage)

            # 更新状态
            self.update_status("统计数据加载完成")

            # 更新时间
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if hasattr(self, "update_time_label"):
                self.update_time_label.configure(text=f"最后更新: {now}")

        except Exception as e:
            logging.error(f"显示统计数据时发生错误: {e}")
            self.show_error(f"显示数据时发生错误: {str(e)}")

    def display_projects_statistics(self, tasks_stats: List[Dict[str, Any]]):
        """显示项目统计"""
        if not hasattr(self, "projects_data_frame"):
            return

        # 清空现有内容
        for widget in self.projects_data_frame.winfo_children():
            widget.destroy()

        if not tasks_stats:
            no_data_label = ctk.CTkLabel(self.projects_data_frame, text="暂无项目统计数据", font=ctk.CTkFont(size=12))
            no_data_label.pack(pady=50)
            return

        # 创建表格头部
        header_frame = ctk.CTkFrame(self.projects_data_frame)
        header_frame.pack(fill="x", padx=10, pady=5)

        # 排名标签
        rank_label = ctk.CTkLabel(header_frame, text="排名", font=ctk.CTkFont(size=12, weight="bold"), width=60)
        rank_label.pack(side="left", padx=5)

        # 项目名称标签
        name_label = ctk.CTkLabel(header_frame, text="项目名称", font=ctk.CTkFont(size=12, weight="bold"), width=200)
        name_label.pack(side="left", padx=5)

        # 构建次数标签
        count_label = ctk.CTkLabel(header_frame, text="构建次数", font=ctk.CTkFont(size=12, weight="bold"), width=100)
        count_label.pack(side="left", padx=5)

        # 进度条标签
        progress_label = ctk.CTkLabel(header_frame, text="占比", font=ctk.CTkFont(size=12, weight="bold"), width=300)
        progress_label.pack(side="left", padx=5)

        # 添加分隔线
        separator = ctk.CTkFrame(self.projects_data_frame, height=2)
        separator.pack(fill="x", padx=10, pady=5)

        # 按构建次数排序
        sorted_tasks = sorted(tasks_stats, key=lambda x: x.get("count", 0), reverse=True)
        max_count = max([task.get("count", 0) for task in sorted_tasks]) if sorted_tasks else 1

        # 显示每个项目的统计
        for i, task in enumerate(sorted_tasks):
            item_frame = ctk.CTkFrame(self.projects_data_frame)
            item_frame.pack(fill="x", padx=10, pady=2)

            # 排名
            rank_label = ctk.CTkLabel(item_frame, text=f"#{i + 1}", width=60)
            rank_label.pack(side="left", padx=5)

            # 项目名称
            name_label = ctk.CTkLabel(item_frame, text=task.get("prod_name", "未知"), width=200)
            name_label.pack(side="left", padx=5)

            # 构建次数
            count = task.get("count", 0)
            count_label = ctk.CTkLabel(item_frame, text=str(count), width=100)
            count_label.pack(side="left", padx=5)

            # 进度条
            progress_value = (count / max_count) if max_count > 0 else 0
            progress_bar = ctk.CTkProgressBar(item_frame, width=300)
            progress_bar.set(progress_value)
            progress_bar.pack(side="left", padx=5)

            # 百分比
            percentage = (count / sum([t.get("count", 0) for t in sorted_tasks])) * 100 if sorted_tasks else 0
            percentage_label = ctk.CTkLabel(item_frame, text=f"{percentage:.1f}%", width=60)
            percentage_label.pack(side="left", padx=5)

    def display_users_statistics(self, packer_usage: List[Dict[str, Any]]):
        """显示用户统计"""
        if not hasattr(self, "users_data_frame"):
            return

        # 清空现有内容
        for widget in self.users_data_frame.winfo_children():
            widget.destroy()

        if not packer_usage:
            no_data_label = ctk.CTkLabel(self.users_data_frame, text="暂无用户统计数据", font=ctk.CTkFont(size=12))
            no_data_label.pack(pady=50)
            return

        # 创建表格头部
        header_frame = ctk.CTkFrame(self.users_data_frame)
        header_frame.pack(fill="x", padx=10, pady=5)

        # 排名标签
        rank_label = ctk.CTkLabel(header_frame, text="排名", font=ctk.CTkFont(size=12, weight="bold"), width=60)
        rank_label.pack(side="left", padx=5)

        # 用户名称标签
        name_label = ctk.CTkLabel(header_frame, text="用户名称", font=ctk.CTkFont(size=12, weight="bold"), width=200)
        name_label.pack(side="left", padx=5)

        # 使用次数标签
        count_label = ctk.CTkLabel(header_frame, text="使用次数", font=ctk.CTkFont(size=12, weight="bold"), width=100)
        count_label.pack(side="left", padx=5)

        # 进度条标签
        progress_label = ctk.CTkLabel(header_frame, text="占比", font=ctk.CTkFont(size=12, weight="bold"), width=300)
        progress_label.pack(side="left", padx=5)

        # 添加分隔线
        separator = ctk.CTkFrame(self.users_data_frame, height=2)
        separator.pack(fill="x", padx=10, pady=5)

        # 按使用次数排序
        sorted_users = sorted(packer_usage, key=lambda x: x.get("count", 0), reverse=True)
        max_count = max([user.get("count", 0) for user in sorted_users]) if sorted_users else 1

        # 显示每个用户的统计
        for i, user in enumerate(sorted_users):
            item_frame = ctk.CTkFrame(self.users_data_frame)
            item_frame.pack(fill="x", padx=10, pady=2)

            # 排名
            rank_label = ctk.CTkLabel(item_frame, text=f"#{i + 1}", width=60)
            rank_label.pack(side="left", padx=5)

            # 用户名称
            name_label = ctk.CTkLabel(item_frame, text=user.get("author", "未知"), width=200)
            name_label.pack(side="left", padx=5)

            # 使用次数
            count = user.get("count", 0)
            count_label = ctk.CTkLabel(item_frame, text=str(count), width=100)
            count_label.pack(side="left", padx=5)

            # 进度条
            progress_value = (count / max_count) if max_count > 0 else 0
            progress_bar = ctk.CTkProgressBar(item_frame, width=300)
            progress_bar.set(progress_value)
            progress_bar.pack(side="left", padx=5)

            # 百分比
            percentage = (count / sum([u.get("count", 0) for u in sorted_users])) * 100 if sorted_users else 0
            percentage_label = ctk.CTkLabel(item_frame, text=f"{percentage:.1f}%", width=60)
            percentage_label.pack(side="left", padx=5)

    def display_overview(self, tasks_stats: List[Dict[str, Any]], packer_usage: List[Dict[str, Any]]):
        """显示概览"""
        if not hasattr(self, "stats_cards_frame"):
            return

        # 清空现有内容
        for widget in self.stats_cards_frame.winfo_children():
            widget.destroy()

        # 计算概览数据
        total_projects = len(tasks_stats)
        total_builds = sum([task.get("count", 0) for task in tasks_stats])
        total_users = len(packer_usage)
        total_user_builds = sum([user.get("count", 0) for user in packer_usage])

        # 创建统计卡片
        cards_frame = ctk.CTkFrame(self.stats_cards_frame)
        cards_frame.pack(fill="x", pady=20)

        # 项目数量卡片
        project_card = self.create_stat_card(cards_frame, "📈", "项目总数", str(total_projects), "活跃项目数量")
        project_card.pack(side="left", padx=10, expand=True, fill="both")

        # 构建次数卡片
        build_card = self.create_stat_card(cards_frame, "🔨", "总构建次数", str(total_builds), "所有项目的构建次数")
        build_card.pack(side="left", padx=10, expand=True, fill="both")

        # 用户数量卡片
        user_card = self.create_stat_card(cards_frame, "👥", "用户总数", str(total_users), "使用系统的用户数量")
        user_card.pack(side="left", padx=10, expand=True, fill="both")

        # 用户构建卡片
        user_build_card = self.create_stat_card(
            cards_frame, "📊", "用户构建总数", str(total_user_builds), "用户发起的构建次数"
        )
        user_build_card.pack(side="left", padx=10, expand=True, fill="both")

    def create_stat_card(self, parent, icon: str, title: str, value: str, description: str):
        """创建统计卡片"""
        card = ctk.CTkFrame(parent)

        # 图标和标题
        title_frame = ctk.CTkFrame(card)
        title_frame.pack(fill="x", padx=15, pady=10)

        icon_label = ctk.CTkLabel(title_frame, text=icon, font=ctk.CTkFont(size=20))
        icon_label.pack(side="left", padx=5)

        title_label = ctk.CTkLabel(title_frame, text=title, font=ctk.CTkFont(size=14, weight="bold"))
        title_label.pack(side="left", padx=5)

        # 数值
        value_label = ctk.CTkLabel(card, text=value, font=ctk.CTkFont(size=24, weight="bold"))
        value_label.pack(pady=5)

        # 描述
        desc_label = ctk.CTkLabel(card, text=description, font=ctk.CTkFont(size=10))
        desc_label.pack(pady=5)

        return card

    def show_error(self, message: str):
        """显示错误信息"""
        self.update_status(f"错误: {message}")

        # 在所有标签页显示错误
        for frame in [self.projects_data_frame, self.users_data_frame, self.stats_cards_frame]:
            if hasattr(frame, "winfo_children"):
                for widget in frame.winfo_children():
                    widget.destroy()

                error_label = ctk.CTkLabel(frame, text=f"❌ {message}", font=ctk.CTkFont(size=12), text_color="red")
                error_label.pack(pady=50)

    def update_status(self, message: str):
        """更新状态"""
        if hasattr(self, "status_label"):
            self.status_label.configure(text=message)

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
