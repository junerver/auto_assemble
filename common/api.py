"""
封装网络请求
"""

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Optional

import requests

from common.config import config
from common.types import TaskInfo


def download_file(url: str, dest_path: Path):
    try:
        headers = {"PRIVATE-TOKEN": "glpat-xJ1c27FLEcMFvtvn6Gzp"}
        response = requests.get(url, headers=headers, stream=True, timeout=10)
        response.raise_for_status()  # 自动抛出 4xx/5xx 错误
        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        logging.info(f"✅ 下载成功: {url} -> {dest_path}")
    except requests.RequestException as e:
        logging.error(f"❌ 下载失败: {url}\n原因: {e}")


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
