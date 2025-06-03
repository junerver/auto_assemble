from enum import Enum
from queue import PriorityQueue
from threading import Lock, Thread
from typing import Optional, Any, Tuple, Dict
import subprocess
import logging


class TaskType(Enum):
    BUILD = "build"  # 打包任务
    FORK = "fork"  # 派生任务


class TaskManager:
    # 共享的队列锁
    _queue_lock = Lock()
    # 共享的任务执行状态
    _is_task_running = False
    # 当前执行的任务类型
    _current_task_type: Optional[TaskType] = None

    # 为不同类型的任务创建不同的队列
    _task_queues = {TaskType.BUILD: PriorityQueue(), TaskType.FORK: PriorityQueue()}

    # 新增：进程管理
    _running_processes: Dict[str, subprocess.Popen] = {}  # {task_id: process}
    _process_lock = Lock()  # 保护进程字典的线程锁

    @classmethod
    def acquire_task_lock(cls, task_type: TaskType) -> bool:
        """
        获取任务锁，如果返回 False，表示有任务正在运行，需要将任务加入队列，
        如果返回 True，表示没有任务正在运行，可以执行任务，直接启动任务线程执行即可
        """
        with cls._queue_lock:
            # 如果已经有任务在运行，直接返回False
            if cls._is_task_running:
                return False

            # 设置任务运行状态和类型
            cls._is_task_running = True
            cls._current_task_type = task_type
            return True

    @classmethod
    def release_task_lock(cls) -> Optional[Tuple[TaskType, Any]]:
        """释放任务锁，并返回下一个要执行的任务类型和任务"""
        with cls._queue_lock:
            # 先保存当前任务类型
            last_task_type = cls._current_task_type

            # 重置状态
            cls._is_task_running = False
            cls._current_task_type = None

            # 检查所有队列，按优先级顺序返回下一个任务
            # 1. 先检查当前类型的队列
            if last_task_type and not cls._task_queues[last_task_type].empty():
                return last_task_type, cls._task_queues[last_task_type].get()

            # 2. 检查其他类型的队列
            for task_type in TaskType:
                if not cls._task_queues[task_type].empty():
                    return task_type, cls._task_queues[task_type].get()

            return None

    @classmethod
    def add_task_to_queue(cls, task: Any, task_type: TaskType):
        """添加任务到指定类型的队列"""
        with cls._queue_lock:
            cls._task_queues[task_type].put(task)

    @classmethod
    def get_next_task(cls, task_type: TaskType) -> Optional[Any]:
        """获取指定类型队列的下一个任务"""
        with cls._queue_lock:
            if not cls._task_queues[task_type].empty():
                return cls._task_queues[task_type].get()
            return None

    @classmethod
    def get_queue_size(cls, task_type: TaskType) -> int:
        """获取指定类型队列的大小"""
        with cls._queue_lock:
            return cls._task_queues[task_type].qsize()

    @classmethod
    def get_current_task_type(cls) -> Optional[TaskType]:
        """获取当前执行的任务类型"""
        with cls._queue_lock:
            return cls._current_task_type

    @classmethod
    def is_any_task_running(cls) -> bool:
        """检查是否有任务正在运行"""
        with cls._queue_lock:
            return cls._is_task_running

    @classmethod
    def exec_next_task(cls):
        # 释放任务锁并获取下一个任务
        next_task_info = TaskManager.release_task_lock()
        if next_task_info:
            (next_task_type, next_task) = next_task_info
            from webhook.controllers.fork_task_controller import fork_task_worker
            from webhook.controllers.webhook_controller import build_task_worker

            is_build_task = next_task_type is TaskType.BUILD
            next_worker = build_task_worker if is_build_task else fork_task_worker
            Thread(target=next_worker, args=(next_task,), daemon=True).start()

    # 新增：进程管理方法
    @classmethod
    def register_process(cls, task_id: str, process: subprocess.Popen):
        """注册正在运行的进程"""
        with cls._process_lock:
            cls._running_processes[task_id] = process
            logging.info(f"注册进程: task_id={task_id}, pid={process.pid}")

    @classmethod
    def unregister_process(cls, task_id: str):
        """注销进程"""
        with cls._process_lock:
            process = cls._running_processes.pop(task_id, None)
            if process:
                logging.info(f"注销进程: task_id={task_id}, pid={process.pid}")

    @classmethod
    def kill_process(cls, task_id: str) -> bool:
        """强制终止指定任务的进程"""
        with cls._process_lock:
            process = cls._running_processes.get(task_id)
            if process:
                try:
                    process.kill()
                    logging.info(f"强制终止进程: task_id={task_id}, pid={process.pid}")
                    Thread(target=cleanup, daemon=True).start()
                    # 成功终止后，从字典中移除进程记录
                    cls._running_processes.pop(task_id, None)
                    logging.info(f"已从进程列表中移除: task_id={task_id}")
                    return True
                except Exception as e:
                    logging.error(f"终止进程失败: task_id={task_id}, error={e}")
                    return False
            else:
                logging.warning(f"未找到要终止的进程: task_id={task_id}")
                return False

    @classmethod
    def get_running_processes(cls) -> Dict[str, subprocess.Popen]:
        """获取所有正在运行的进程"""
        with cls._process_lock:
            return cls._running_processes.copy()

    @classmethod
    def is_process_running(cls, task_id: str) -> bool:
        """检查指定任务的进程是否正在运行"""
        with cls._process_lock:
            return task_id in cls._running_processes


def cleanup():
    """清理分发仓库、基座仓库"""
    from common import git
    from common.config import config

    git.git_reset_and_clean(repo_path=config.ANDROID_UNI_BASE_PATH)
    git.git_reset_and_clean(repo_path=config.DISTRIBUTION_PATH)
