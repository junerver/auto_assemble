"""
封装网络请求
"""

from collections.abc import Callable
from typing import Optional

import requests

from common.config import config
from common.types import TaskInfo

from requests.exceptions import RequestException, JSONDecodeError


def fetch_task_info(
    task_id: str,
    on_success: Optional[Callable[[TaskInfo], None]] = None,
    on_error: Optional[Callable[[str], None]] = None,
) -> None:
    """
    查询指定任务id的任务信息
    Args:
        task_id: 任务ID（字符串）
        on_success: 成功时的回调函数，接收 TaskInfo 对象
        on_error: 失败时的回调函数，接收错误信息字符串
    Returns:
        None
    """
    if not config.SERVER_HOST_URL:
        if on_error:
            on_error("SERVER_HOST_URL is not configured")
        return None

    try:
        response = requests.get(f"{config.SERVER_HOST_URL}/task/{task_id}", timeout=5)
        response.raise_for_status()
        data = response.json()
        if "task" not in data:
            if on_error:
                on_error("Response does not contain 'task' key")
            return None
        task_info = TaskInfo.from_dict(data["task"])
        if on_success:
            on_success(task_info)
    except (RequestException, JSONDecodeError, ValueError) as e:
        if on_error:
            on_error(f"Failed to fetch task info: {str(e)}")
    return None


if __name__ == "__main__":
    fetch_task_info("identify_field,202504271900", lambda x: print(x.to_json()), lambda e: print(f"error: {e}"))
