from win11toast import toast


def show_toast(title, message):
    """显示Windows通知"""
    toast(title, message)


def show_build_toast(task, success=True):
    """显示构建结果通知"""
    status = "✅成功" if success else "❌失败"
    message = f"🗃️项目: {task.prod_name}\n🏗️任务: {task.task_name}\n🧑‍💻作者: {task.author}\n📝标题: {task.commit_title}"
    if not success and task.error:
        message += f"\n错误: {task.error}"
    toast(f"🎉构建通知:{status}", message)
