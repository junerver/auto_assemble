from enum import Enum
from queue import PriorityQueue
from threading import Lock
from typing import Optional, Any, Tuple


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
