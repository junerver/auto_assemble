"""
封装网络请求
"""

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Optional, Union

import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import RequestException, JSONDecodeError
from urllib3.util.retry import Retry

from common.config import config, BuildMode
from common.gitlab import FileType
from common.types import TaskInfo, BuildMetadata, ThirdPartyConfig, ProjectConfig, SignConfig


def fetch_task_info(
    task_id: str,
    on_success: Optional[Callable[[TaskInfo], None]] = None,
    on_error: Optional[Callable[[str], None]] = None,
) -> Optional[TaskInfo]:
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
        return task_info
    except (RequestException, JSONDecodeError, ValueError) as e:
        if on_error:
            on_error(f"Failed to fetch task info: {str(e)}")
    return None


def fetch_task_info_by_res_fp(
    res_fp: str,
    on_success: Optional[Callable[[TaskInfo], None]] = None,
    on_error: Optional[Callable[[str], None]] = None,
) -> Optional[TaskInfo]:
    """
    查询Uni资源包指纹相同的构建任务
    Args:
        res_fp: 资源包指纹
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
        params = {"res_fp": res_fp}
        response = requests.get(f"{config.SERVER_HOST_URL}/api/task", timeout=5, params=params)
        response.raise_for_status()
        data = response.json()
        if "task" not in data:
            if on_error:
                on_error("Response does not contain 'task' key")
            return None
        task_info = TaskInfo.from_dict(data["task"])
        if on_success:
            on_success(task_info)
        return task_info
    except (RequestException, JSONDecodeError, ValueError) as e:
        if on_error:
            on_error(f"Failed to fetch task info: {str(e)}")
    return None


def record_task_metadata(
    task_id: str,
    metadata: BuildMetadata,
    on_success: Optional[Callable[[], None]] = None,
    on_error: Optional[Callable[[str], None]] = None,
) -> bool:
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
) -> Optional[list[ThirdPartyConfig]]:
    """
    查询指定项目名称的第三方服务配置信息，用于 auto_assemble
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
        return third_party_configs
    else:
        # 如果从服务器接口读取失败，则使用本地解析
        if on_error:
            on_error(f"Failed to fetch task info: {response.status_code} {response.text}")
        return None


def fetch_project_info_by_prod_name(
    prod_name: str,
    on_success: Optional[Callable[[ProjectConfig], None]] = None,
    on_error: Optional[Callable[[str], None]] = None,
) -> Optional[ProjectConfig]:
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
        project_config: ProjectConfig = ProjectConfig.from_dict(data["project_config"])
        if on_success:
            on_success(project_config)
        return project_config
    else:
        # 如果从服务器接口读取失败，则使用本地解析
        if on_error:
            on_error(f"Failed to fetch task info: {response.status_code} {response.text}")
        return None


def record_project_sign_config(
    project_id: str,
    sign_config: SignConfig,
    on_success: Optional[Callable[[], None]] = None,
    on_error: Optional[Callable[[str], None]] = None,
):
    """
    更新项目的签名配置
    Args:
        project_id: 项目id（uui）
        sign_config: 签名配置
        on_success:
        on_error:

    Returns:

    """
    response = requests.post(
        f"{config.SERVER_HOST_URL}/api/config/project/{project_id}/update",
        json=sign_config.to_dict(),
    )
    response.raise_for_status()
    logging.info("更新签名配置成功")


def fetch_project_info_by_url(
    project_url: str,
    on_success: Optional[Callable[[dict], None]] = None,
    on_error: Optional[Callable[[str], None]] = None,
) -> Optional[dict]:
    """
    查询指定项目名称的配置信息，用于cbr
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
        return data
    else:
        if on_error:
            on_error(f"Failed to fetch project info: {response.status_code} {response.text}")
        return None


def fetch_fork_task_info(
    base_url: str,
    fork_task_id: str,
    on_success: Optional[Callable[[dict], None]] = None,
    on_error: Optional[Callable[[str], None]] = None,
) -> Optional[dict]:
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
        return None
    fork_task_info = response.json()["fork_task"]
    if on_success:
        on_success(fork_task_info)
    return fork_task_info


def record_task_res_fp(
    task_id: str,
    res_fp: str,
    on_success: Optional[Callable[[str], None]] = None,
    on_error: Optional[Callable[[str], None]] = None,
):
    """
    记录构建任务的资源包指纹信息，仅在需要执行构建时添加，避免镜像任务太多污染搜索
    """
    try:
        response = requests.post(f"{config.SERVER_HOST_URL}/api/task/{task_id}/update", json={"res_fp": res_fp})
        if response.ok:
            if on_success:
                message = response.json().get("message", response.text)
                on_success(message)
        else:
            if on_error:
                on_error(f"Failed to record task res_fp: {response.status_code} {response.text}")
    except Exception as e:
        if on_error:
            on_error(f"Exception occurred while recording res_fp: {e}")


def submit_cbr_form(
    prod_name: str,
    author: str,
    commit_message: str,
    readme_path: Optional[Union[str, Path]],
    res_zip_path: Optional[Union[str, Path]],
    timeout: int = 30,
    max_retries: int = 3,
    backoff_factor: float = 0.3,
):
    """
    封装的 /api/cbr 接口请求函数，支持 pathlib.Path 类型的文件路径

    优化特性：
    - 使用上下文管理器确保文件正确关闭
    - 添加重试机制处理网络连接问题
    - 改进错误处理和日志记录
    - 优化连接管理和超时设置

    Args:
        prod_name: 产品名称
        author: 作者信息
        commit_message: 提交信息
        readme_path: README.md 文件路径（str 或 Path 对象）
        res_zip_path: 资源 zip 文件路径（str 或 Path 对象）
        timeout: 请求超时时间（秒），默认为 30
        max_retries: 最大重试次数，默认为 3
        backoff_factor: 重试间隔因子，默认为 0.3

    Returns:
        dict: 接口返回的 JSON 数据

    Raises:
        requests.RequestException: 网络请求错误
        FileNotFoundError: 文件路径无效
        ValueError: 必要参数缺失
    """
    # 转换文件路径为 Path 对象
    readme_path = Path(readme_path) if readme_path else None
    res_zip_path = Path(res_zip_path) if res_zip_path else None

    # 验证文件路径
    if readme_path and not readme_path.is_file():
        raise FileNotFoundError(f"README 文件未找到: {readme_path}")
    if res_zip_path and not res_zip_path.is_file():
        raise FileNotFoundError(f"资源 zip 文件未找到: {res_zip_path}")

    # 准备表单数据
    data = {"prod_name": prod_name, "author": author, "commit_message": commit_message}

    # 配置重试策略
    retry_strategy = Retry(
        total=max_retries,
        status_forcelist=[429, 500, 502, 503, 504],
        backoff_factor=backoff_factor,
        allowed_methods=["POST"],
    )

    # 创建会话并配置适配器
    session = requests.Session()
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # 构造请求头 - 简化设置，避免与multipart处理冲突
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    # 使用上下文管理器确保文件正确关闭
    files = {}
    file_handles = []

    try:
        # 准备文件数据 - 使用更通用的MIME类型
        if readme_path:
            readme_file = open(readme_path, "rb")
            file_handles.append(readme_file)
            files["readme"] = ("README.md", readme_file, "text/plain")

        if res_zip_path:
            zip_file = open(res_zip_path, "rb")
            file_handles.append(zip_file)
            files["res_zip"] = (res_zip_path.name, zip_file, "application/octet-stream")

        # 发送 POST 请求 - 启用流式传输
        logging.info(f"正在提交 CBR 请求: {prod_name}")

        # 记录文件大小信息
        if readme_path:
            readme_size = readme_path.stat().st_size
            logging.info(f"README 文件大小: {readme_size} 字节")
        if res_zip_path:
            zip_size = res_zip_path.stat().st_size
            logging.info(f"ZIP 文件大小: {zip_size} 字节")

        response = session.post(
            f"{config.SERVER_HOST_URL}/api/cbr",
            data=data,
            files=files,
            headers=headers,
            timeout=timeout,
            stream=True,  # 启用流式传输
        )
        response.raise_for_status()  # 检查 HTTP 状态码

        result = response.json()
        logging.info(f"CBR 请求提交成功: {prod_name}")
        return result

    except requests.exceptions.ConnectionError as e:
        error_msg = f"连接错误，请检查网络连接和服务器状态: {str(e)}"
        logging.error(error_msg)
        raise Exception(error_msg)

    except requests.exceptions.Timeout as e:
        error_msg = f"请求超时，请尝试增加超时时间或检查网络状况: {str(e)}"
        logging.error(error_msg)
        raise Exception(error_msg)

    except requests.exceptions.HTTPError as e:
        error_msg = f"HTTP 错误 {e.response.status_code}: {str(e)}"
        logging.error(error_msg)
        raise Exception(error_msg)

    except requests.RequestException as e:
        error_msg = f"请求失败: {str(e)}"
        logging.error(error_msg)
        raise Exception(error_msg)

    except JSONDecodeError as e:
        error_msg = f"响应数据解析失败: {str(e)}"
        logging.error(error_msg)
        raise Exception(error_msg)

    finally:
        # 确保所有文件句柄都被正确关闭
        for file_handle in file_handles:
            try:
                file_handle.close()
            except Exception as e:
                logging.warning(f"关闭文件句柄时出现警告: {str(e)}")

        # 关闭会话
        try:
            session.close()
        except Exception as e:
            logging.warning(f"关闭会话时出现警告: {str(e)}")


def download_task_file(task_id: str, dest_dir: Path, file_type: FileType) -> Path:
    """
    通过后台接口执行下载任务
    Args:
        task_id: 任务ID
        dest_dir: 目标目录路径
        file_type: 文件类型

    Returns:
        Path: 下载文件的路径或解压后的目录路径
    """
    # 确保目标目录存在
    dest_dir.mkdir(parents=True, exist_ok=True)

    # 下载文件
    response = requests.get(f"{config.SERVER_HOST_URL}/api/task/{task_id}/download?file_type={file_type}", stream=True)
    response.raise_for_status()  # 确保请求成功

    # 从响应头获取文件名，如果没有则使用默认名称
    content_disposition = response.headers.get("content-disposition")
    filename = f"{task_id}_{file_type}"
    if content_disposition and "filename=" in content_disposition:
        filename = content_disposition.split("filename=")[1].strip('"')

    # 将文件下载到dest_dir
    file_path = dest_dir / filename
    with open(file_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    # 判断文件是否为压缩包
    is_archive = False
    # 通过文件扩展名判断
    if filename.lower().endswith((".zip", ".rar")):
        is_archive = True

    # 如果是压缩包，则解压并删除原文件
    if is_archive:
        try:
            from common.extract import modern_extract

            logging.info(f"解压文件: {file_path} 到 {dest_dir}")
            modern_extract(file_path, dest_dir)

            # 删除压缩文件
            file_path.unlink()

            return dest_dir
        except Exception as e:
            # 如果解压失败，保留压缩文件以便调试
            logging.exception(f"解压文件失败: {str(e)}")
            raise Exception(f"解压文件失败: {str(e)}")
    else:
        # 如果不是压缩包，直接返回文件路径
        logging.info(f"下载的文件不是压缩包，保留原文件: {file_path}")
        return file_path


def local_file_push(task_id: str, build_mode: BuildMode, md5: str):
    """
    本地文件模式时，需要模拟触发webhook
    Returns:
        dict: 接口返回的 JSON 数据
    """
    params = {
        "build_mode": build_mode,
        "md5": md5,
    }
    response = requests.get(f"{config.SERVER_HOST_URL}/api/task/{task_id}/response", params=params)
    return response.json()
