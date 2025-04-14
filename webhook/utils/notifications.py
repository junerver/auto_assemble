import logging
import threading

from win11toast import toast

from webhook.services.task_service import BuildTask


def show_toast(title, message):
    """显示Windows通知"""
    try:
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
    except Exception as e:
        logging.error(f"显示通知时发生错误: {str(e)}")


def show_build_toast(task: BuildTask, success=True):
    """显示构建结果通知"""
    status = "✅成功" if success else "❌失败"
    message = f"🗃️项目: {task.prod_name}\n🏗️任务: {task.task_name}\n🧑‍💻作者: {task.author}\n📝标题: {task.commit_title}"
    if not success and task.error:
        message += f"\n错误: {task.error}"
    show_toast(f"🎉构建通知:{status}", message)
