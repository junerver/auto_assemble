import json
import logging
from datetime import datetime

from auto_assemble.err_code import format_error
from ..models.task import Task
from ..utils.notifications import show_toast
from ..utils.validators import is_valid_build_task, parse_build_task


class TaskService:
    @staticmethod
    def handle_webhook_request(data):
        """处理webhook请求并创建任务

        Args:
            data: webhook请求数据

        Returns:
            tuple: (task, message, status_code)
            - task: 创建的任务对象，如果没有创建则为None
            - message: 处理结果消息
            - status_code: HTTP状态码
        """
        # 验证提交信息
        commits = data.get("commits", [])
        if not commits:
            return None, "No file changes in commit", 200

        added_files = commits[0].get("added", [])
        if not is_valid_build_task(added_files):
            logging.warning(
                f"收到无效的构建请求:\n {json.dumps(commits, ensure_ascii=False, indent=2)}"
            )
            return None, "Not a valid build task", 200

        # 解析任务信息
        commit_info = commits[0]
        prod_name, task_name = parse_build_task(added_files)

        # 显示收到构建请求的toast提示
        show_toast(
            "📜收到构建请求",
            f"🗃️项目: {prod_name}\n🏗️任务: {task_name}\n🧑‍💻作者: {commit_info.get('author', {}).get('name', '未知')}\n📝标题: {commit_info.get('title', '无标题')}",
        )

        # 创建任务
        task = TaskService.create_task(
            prod_name=prod_name,
            task_name=task_name,
            commit_info=commit_info,
            priority=0,
        )

        return task, "Task created successfully", 200

    @staticmethod
    def create_task(prod_name, task_name, commit_info=None, priority=0, retries=0):
        """创建任务"""
        task = Task(
            id=f"{prod_name},{task_name}",
            prod_name=prod_name,
            task_name=task_name,
            priority=priority,
            retries=retries,
            status="pending",
            created_at=datetime.now(),
        )

        if commit_info:
            task.author = commit_info.get("author", {}).get("name")
            task.commit_title = commit_info.get("title")
            task.commit_message = commit_info.get("message")
            task.commit_url = commit_info.get("url")
            task.commit_hash = commit_info.get("id")

            try:
                timestamp = commit_info.get("timestamp")
                if timestamp:
                    task.created_at = datetime.strptime(
                        timestamp, "%Y-%m-%dT%H:%M:%S%z"
                    )
            except (ValueError, TypeError):
                pass

        task.save()
        return task

    @staticmethod
    def get_task(task_id):
        """通过任务id获取任务详情"""
        return Task.get_by_id(task_id)

    @staticmethod
    def get_running_task():
        """获取正在执行的任务"""
        return Task.get_running_task()

    @staticmethod
    def get_pending_tasks():
        """获取待执行任务"""
        return Task.get_pending_tasks()

    @staticmethod
    def get_recent_tasks(limit=5):
        """获取最近任务"""
        return Task.get_recent_tasks(limit)

    @staticmethod
    def update_task_status(task_id, status, error=None):
        """更新任务状态"""
        task = Task.get_by_id(task_id)
        if task:
            task.update_status(status, error)
            return task
        return None

    @staticmethod
    def get_queue_status(limit: int = 5, build_mode: str | None = None):
        """
        获取队列状态

        Args:
            limit: 返回的任务数量限制
            build_mode: 构建模式，可选值为 dev/test/release，为 None 时不进行筛选
        """
        running_task = Task.get_running_task()
        pending_tasks = Task.get_pending_tasks()
        recent_tasks = Task.get_recent_tasks(limit=limit, build_mode=build_mode)

        return {
            "running_task": running_task.to_dict() if running_task else None,
            "pending_tasks": [task.to_dict() for task in pending_tasks],
            "queue_size": len(pending_tasks),
            "recent_tasks": [task.to_dict() for task in recent_tasks],
        }

    @staticmethod
    def stop_task(task_id):
        """停止运行中的任务

        Args:
            task_id: 任务ID

        Returns:
            tuple: (task, message, status_code)
            - task: 更新后的任务对象，如果任务不存在或不在运行中则为None
            - message: 处理结果消息
            - status_code: HTTP状态码
        """
        task = Task.get_by_id(task_id)
        if not task:
            return None, "Task not found", 404

        if task.status != "running":
            return None, "Task is not running", 400

        task.update_status("failed", format_error(10003))
        return task, "Task stopped successfully", 200

    @staticmethod
    def get_tasks_statistics():
        """获取所有任务的统计情况"""
        return Task.get_tasks_statistics()

    @staticmethod
    def get_packer_usage_statistics():
        """获取打包机使用人员统计情况"""
        return Task.get_packer_usage_statistics()
