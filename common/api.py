"""
封装网络请求
"""

from collections.abc import Callable
from typing import Optional

import requests

from common.config import config
from common.types import TaskInfo


def fetch_task_info(
    task_id: str,
    on_success: Optional[Callable[[TaskInfo], None]],
    on_error: Optional[Callable[[], None]],
):
    """
    查询指定任务id的任务信息
    Args:
        task_id: 任务id
        on_success: 成功时的回调
        on_error: 失败回调

    Returns:

    """
    response = requests.get(f"{config.SERVER_HOST_URL}/task/{task_id}")
    if response.status_code == 200:
        task_info = TaskInfo.from_dict(response.json()["task"])
        if on_success is not None:
            on_success(task_info)
    else:
        if on_error is not None:
            on_error()


if __name__ == "__main__":
    fetch_task_info("identify_field,202504271900", lambda x: print(x.to_json()), lambda: print("error"))
