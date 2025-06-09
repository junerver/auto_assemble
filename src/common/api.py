"""
封装网络请求
"""

import logging
from collections.abc import Callable
from typing import Optional

import requests

from common.config import config
from common.types import TaskInfo, BuildMetadata, ThirdPartyConfig

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


def record_task_metadata(
    task_id: str,
    metadata: BuildMetadata,
    on_success: Optional[Callable[[], None]] = None,
    on_error: Optional[Callable[[str], None]] = None,
):
    """
    为指定的任务id添加构建元数据内容
    Args:
        task_id:
        metadata:
        on_success:
        on_error:

    Returns:
        bool: 网络请求是否成功
    """
    try:
        request_url = f"{config.SERVER_HOST_URL}/api/metadata/{task_id}"
        response = requests.post(request_url, json=metadata)
        if response.status_code != 201:
            if on_error:
                on_error(f"调用接口提交元数据失败: {response.status_code} {response.text}")
            return False
        if on_success:
            on_success()
        return True
    except Exception as e:
        logging.exception(f"调用接口提交元数据失败: {e}")
        if on_error:
            on_error(f"调用接口提交元数据失败: {e}")
        return False


def fetch_third_party_configs(
    prod_name: str,
    on_success: Optional[Callable[[list[ThirdPartyConfig]], None]] = None,
    on_error: Optional[Callable[[str], None]] = None,
) -> None:
    """
    查询指定项目名称的第三方服务配置信息
    Args:
        prod_name: 项目名称（字符串）
        on_success: 获取成功时的回调函数，接收 ThirdPartyConfig 列表
        on_error: 获取失败时的回调函数，接收错误信息字符串
    Returns:

    """
    # 解析第三方配置读取，修改为从服务器接口读取，不再解析yaml代码块
    response = requests.get(f"{config.SERVER_HOST_URL}/api/config/project?name={prod_name}")
    if response.status_code == 200:
        data = response.json()
        third_party_configs: list[ThirdPartyConfig] = data["third_party_configs"]
        if on_success:
            on_success(third_party_configs)
    else:
        # 如果从服务器接口读取失败，则使用本地解析
        if on_error:
            on_error(f"Failed to fetch task info: {response.status_code} {response.text}")


def fetch_project_info_by_url(
    project_url: str,
    on_success: Optional[Callable[[dict], None]] = None,
    on_error: Optional[Callable[[str], None]] = None,
) -> None:
    """
    查询指定项目名称的配置信息
    Args:
        project_url: git项目地址
        on_success: 获取成功时的回调函数，接收 dict
        on_error: 获取失败时的回调函数，接收错误信息字符串
    Returns:

    """
    params = {"url": project_url}
    response = requests.get(f"{config.SERVER_HOST_URL}/api/config/project", params=params)
    if response.status_code == 200:
        data = response.json()
        if on_success:
            on_success(data)
    else:
        if on_error:
            on_error(f"Failed to fetch project info: {response.status_code} {response.text}")


def fetch_fork_task_info(
    base_url: str,
    fork_task_id: str,
    on_success: Optional[Callable[[dict], None]] = None,
    on_error: Optional[Callable[[str], None]] = None,
):
    """
    请求派生任务详情
    Args:
        base_url:
        fork_task_id:
        on_success:
        on_error:

    Returns:

    """
    response = requests.get(f"{base_url}/api/fork_task/{fork_task_id}")
    if response.status_code != 200:
        if on_error:
            on_error(f"Failed to fetch fork task info: {response.status_code} {response.text}")
    fork_task_info = response.json()["fork_task"]
    if on_success:
        on_success(fork_task_info)


if __name__ == "__main__":
    fetch_task_info("identify_field,202504271900", lambda x: print(x.to_json()), lambda e: print(f"error: {e}"))
