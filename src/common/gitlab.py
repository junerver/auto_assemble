import logging
import shutil
import urllib.parse
from pathlib import Path
from typing import Literal, Generator, Union

import requests
from fastapi import HTTPException
from zipstream.ng import ZipStream

from common.commit_label import parse_build_req_message
from common.config import config
from common.task_util import local_task_dir
from common.types import TaskInfo


def _download_gitlab_lfs_file_stream(
    gitlab_url: str, access_token: str, project_id: str, ref_hash: str, file_name: str, is_lfs: bool
):
    """流式下载 GitLab 文件并返回生成器

    Args:
        gitlab_url: GitLab 服务器地址
        access_token: 访问令牌
        project_id: 项目 ID
        ref_hash: 指向的 hash
        file_name: 要下载的文件名（identify_field/202504271900/README.md）
        is_lfs: 是否为 LFS 存储

    Yields:
        文件内容的字节流
    """
    try:
        normalized_path = file_name.replace("\\", "/")
        encoded_path = urllib.parse.quote(normalized_path, safe="")
        # 构造 API 请求 URL
        api_url = f"{gitlab_url}/api/v4/projects/{project_id}/repository/files/{encoded_path}/raw"
        params = {"ref": ref_hash, "lfs": is_lfs}
        headers = {"Private-Token": access_token, "Content-Type": "application/json"}

        # 发起流式请求
        with requests.get(api_url, headers=headers, params=params, stream=True) as response:
            response.raise_for_status()  # 抛出 4xx/5xx 错误
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    yield chunk
        logging.info(f"✅ 流式传输成功: {api_url}")
    except requests.RequestException as e:
        logging.error(f"❌ 流式传输失败\n原因: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to download file: {str(e)}")


def _download_gitlab_lfs_file(
    gitlab_url: str, access_token: str, project_id: str, ref_hash: str, file_name: str, dest_path: Path, is_lfs: bool
):
    """下载 GitLab 文件并保存到本地

    Args:
        gitlab_url: GitLab 服务器地址
        access_token: 访问令牌
        project_id: 项目 ID
        ref_hash: 指向的 hash
        file_name: 要下载的文件名（identify_field/202504271900/README.md）
        dest_path: 文件保存的目标路径
        is_lfs: 是否为 LFS 存储
    """
    try:
        # 确保目标目录存在
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        # 使用流式下载函数
        with open(dest_path, "wb") as f:
            for chunk in _download_gitlab_lfs_file_stream(
                gitlab_url, access_token, project_id, ref_hash, file_name, is_lfs
            ):
                f.write(chunk)
        logging.info(f"✅ 下载成功: {gitlab_url} -> {dest_path}")
    except HTTPException as e:
        # 捕获 download_gitlab_lfs_file_stream 抛出的 HTTPException
        logging.error(f"❌ 下载失败\n原因: {e.detail}")
        raise
    except Exception as e:
        logging.error(f"❌ 下载失败\n原因: {e}")
        raise


def _download_file(task_info: TaskInfo, relative_path: str, dest_path: Path) -> Path:
    """
    对外暴露的下载文件函数
    Args:
        task_info: 项目信息
        relative_path: 相对根目录的相对路径
        dest_path: 目标文件路径

    Returns:
        Path: 下载完成后文件路径
    """
    file_name = relative_path.replace(task_info.task_path(), "")
    if not task_info.is_local_file():
        ref_hash = task_info.response_hash
        logging.info(f"开始下载文件: {file_name}")
        _download_gitlab_lfs_file(
            config.GITLAB_URL,
            config.ACCESS_TOKEN,
            config.PROJECT_ID,
            ref_hash,
            file_name,
            dest_path,
            True,
        )
    else:
        # 本地模式：
        logging.info("本地模式，从本地目录拷贝文件...")
        build_mode, _ = parse_build_req_message(task_info.commit_title)
        task_dir = local_task_dir(task_info.id, build_mode)
        file_path = task_dir / file_name
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {relative_path}")
        shutil.copy(file_path, dest_path)

    logging.info(f"✅ 下载成功: {file_name} -> {dest_path}")
    return dest_path


def _download_file_stream(task_info: TaskInfo, relative_path: str) -> Generator[bytes, None, None]:
    """
    对外暴露的流式下载文件函数
    Args:
        task_info: 指向任务信息
        relative_path: 相对根目录的相对路径

    Yields:
        文件内容的字节流

    Raises:
        HTTPException: 如果下载失败，抛出错误
    """
    file_name = relative_path.replace(task_info.task_path(), "")
    if not task_info.is_local_file():
        ref_hash = task_info.response_hash
        logging.info(f"开始流式下载文件: {relative_path}")
        for chunk in _download_gitlab_lfs_file_stream(
            config.GITLAB_URL,
            config.ACCESS_TOKEN,
            config.PROJECT_ID,
            ref_hash,
            relative_path,
            True,
        ):
            yield chunk
    else:
        # 本地模式：
        logging.info("本地模式，开始流式下载文件...")
        build_mode, _ = parse_build_req_message(task_info.commit_title)
        task_dir = local_task_dir(task_info.id, build_mode)
        file_path = task_dir / file_name
        if file_path.exists():
            with open(file_path, "rb") as f:
                for chunk in f:
                    yield chunk
    logging.info(f"✅ 流式下载成功: {file_name}")


def _generate_zip_stream(generator_dict: dict[str, Generator[bytes, None, None]]) -> ZipStream:
    """创建压缩包zip流

    Args:
        generator_dict: 生成器字典，key是文件名称，value是生成器

    Returns:
        ZipStream: zip流
    """
    z = ZipStream(compress_level=3)
    for path, stream in generator_dict.items():
        z.add(stream, path)
    # 返回 zip 生成器
    return z


# 下载文件的类型：全部文件、uni资源包、readme、metadata、apk、release产物（元数据+apk）、全产物（请求文件两个，响应必备两个）
FileType = Literal["res", "readme", "metadata", "apk", "release", "all"]


def compare_readme_file(task_info: TaskInfo, readme_path: Path) -> bool:
    """比较当前任务的README是否与之前任务的readme相同，先下载资源包相同任务的 readme，然后进行文本比较"""
    origin_readme_path = _download_file(
        task_info, task_info.readme_path(), config.TEMP_PATH / task_info.project / task_info.task
    )
    with open(origin_readme_path, "r", encoding="utf-8") as f1, open(readme_path, "r", encoding="utf-8") as f2:
        return f1.read() == f2.read()


def download_task_files_stream(
    task_info: TaskInfo, file_type: FileType
) -> tuple[Union[Generator[bytes, None, None], ZipStream], str]:
    """通过file_type流式下载任务中对应指定类型的文件

    Args:
        task_info: 任务信息
        file_type: 文件类型，字面量

    Returns:
        tuple[Generator[bytes, None, None], str]: 流式数据生成器和文件名
    """
    match file_type:
        case "res":
            return _download_file_stream(task_info, task_info.res_path()), f"{task_info.task}.zip"
        case "readme":
            return _download_file_stream(task_info, task_info.readme_path()), "README.md"
        case "metadata":
            return _download_file_stream(task_info, task_info.metadata_path()), "release-metadata.md"
        case "apk":
            return _download_file_stream(task_info, task_info.apk_path()), task_info.apk_name()
        case "release":
            # release产物: 元数据、apk
            return _generate_zip_stream(
                {
                    "release-metadata.md": _download_file_stream(task_info, task_info.metadata_path()),
                    task_info.apk_name(): _download_file_stream(task_info, task_info.apk_path()),
                }
            ), f"{task_info.task}_release.zip"
        case "all":
            # 全部文件: 资源包、README、元数据、apk
            return _generate_zip_stream(
                {
                    f"{task_info.task}.zip": _download_file_stream(task_info, task_info.res_path()),
                    "README.md": _download_file_stream(task_info, task_info.readme_path()),
                    "release-metadata.md": _download_file_stream(task_info, task_info.metadata_path()),
                    task_info.apk_name(): _download_file_stream(task_info, task_info.apk_path()),
                }
            ), f"{task_info.task}_all.zip"
    raise HTTPException(status_code=400, detail=f"Invalid file type: {file_type}")


def download_task_resp(task_info: TaskInfo, dest_dir: Path) -> tuple[Path, Path, Path]:
    """下载构建响应文件到目标目录

    针对指定任务下载或创建构建响应文件：
    - README.md 构建自述
    - xxxx_obfuscated.bak 混淆后的资源文件（实际装载到壳工程的资源）
    - xxxx.apk 构建产物

    下载时文件名称保持与原来格式一致，例如旧构建是dev，下载的文件是带 _debug 的，那下载的文件也是如此（只有test可以迁移到release，正常都是同模式迁移）
    Args:
        task_info: 要下载的任务
        dest_dir: 目标目录

    """
    target_task = dest_dir.name
    build_mode = parse_build_req_message(task_info.commit_title)[0]
    new_apk_file_name = f"{target_task}_debug.apk" if build_mode == "dev" else f"{target_task}.apk"

    metadata_md = dest_dir / "release-metadata.md"
    obfuscated_bak = dest_dir / f"{target_task}_obfuscated.bak"
    apk_file = dest_dir / new_apk_file_name
    _download_file(task_info.response_hash, task_info.metadata_path(), metadata_md)
    _download_file(task_info.response_hash, task_info.obfuscated_path(), obfuscated_bak)
    _download_file(task_info.response_hash, task_info.apk_path(), apk_file)
    return metadata_md, obfuscated_bak, apk_file
