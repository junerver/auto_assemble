import logging
import sys
import threading

from ..models.task import Task


def show_toast(title, message):
    """显示Windows通知"""
    try:
        if sys.platform == "win32":
            from win11toast import toast

            # 创建一个新的事件循环
            def run_toast():
                import asyncio

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                toast(title, message)
                loop.close()

            # 在新线程中运行toast
            thread = threading.Thread(target=run_toast)
            thread.start()
        else:
            logging.info(f"Toast notification: {title} - {message}")
    except Exception as e:
        logging.error(f"显示通知时发生错误: {str(e)}")


def show_build_toast(task: Task, success: bool):
    """显示构建结果toast通知"""
    try:
        if success:
            title = "✅构建成功"
            message = f"🗃️项目: {task.prod_name}\n🏗️任务: {task.task_name}\n⏱️耗时: {format_duration(task.started_at, task.completed_at)}"
        else:
            title = "❌构建失败"
            message = f"🗃️项目: {task.prod_name}\n🏗️任务: {task.task_name}\n⏱️耗时: {format_duration(task.started_at, task.completed_at)}\n❌错误: {task.error}"

        show_toast(title, message)
    except Exception as e:
        logging.error(f"显示构建结果toast通知时发生错误: {str(e)}")


def format_duration(start_time, end_time):
    """格式化时间间隔"""
    if not start_time or not end_time:
        return "未知"
    duration = end_time - start_time
    seconds = duration.total_seconds()
    if seconds < 60:
        return f"{int(seconds)}秒"
    elif seconds < 3600:
        return f"{int(seconds // 60)}分{int(seconds % 60)}秒"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}小时{minutes}分"
