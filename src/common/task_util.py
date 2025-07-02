from pathlib import Path

from common.config import config


def local_task_dir(task_id: str, build_mode: str) -> Path:
    """通过传入的task_id和build_mode，返回本地任务目录

    目录结构：
    - temp
        - build_mode
            - prod_name
                - task_id

    Args:
        task_id: 任务id，格式为prod_name,task_id
        build_mode: 构建模式

    Returns:
        Path: 任务目录
    """
    prod_name, task = task_id.split(",")
    temp_task_dir = config.TEMP_PATH / build_mode / prod_name / task
    return temp_task_dir
