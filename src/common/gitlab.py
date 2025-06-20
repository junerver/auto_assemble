import logging
import urllib.parse
from pathlib import Path
from typing import Optional, Literal

import requests

from common.commit_label import parse_build_req_message
from common.config import config
from common.types import TaskInfo


def _download_gitlab_lfs_file(
    gitlab_url: str, access_token: str, project_id: str, ref_hash: str, file_name: str, dest_path: Path, is_lfs: bool
):
    """下载gitlab文件

    Args:
        gitlab_url: gitlab 服务器地址
        access_token: 访问令牌
        project_id: 项目id
        ref_hash: 指向的hash
        file_name: 要下载的文件名（identify_field/202504271900/README.md）
        dest_path: 文件保存的目标路径
        is_lfs: 是否为lfs存储

    Returns:

    """
    try:
        normalized_path = file_name.replace("\\", "/")
        encoded_path = urllib.parse.quote(normalized_path, safe="")
        # 构造API请求URL
        api_url = f"{gitlab_url}/api/v4/projects/{project_id}/repository/files/{encoded_path}/raw"
        params = {"ref": ref_hash, "lfs": is_lfs}
        headers = {"Private-Token": access_token, "Content-Type": "application/json"}
        # 确保目标目录存在
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        response = requests.get(api_url, headers=headers, params=params, stream=True)
        response.raise_for_status()  # 自动抛出 4xx/5xx 错误
        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        logging.info(f"✅ 下载成功: {api_url} -> {dest_path}")
    except requests.RequestException as e:
        logging.error(f"❌ 下载失败\n原因: {e}")


def download_file(ref_hash: str, file_name: str, dest_path: Path) -> Path:
    """
    对外暴露的下载文件函数
    Args:
        ref_hash:
        file_name: 相对根目录的相对路径
        dest_path: 目标文件路径

    Returns:
        Path: 下载完成后文件路径
    """
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
    logging.info(f"✅ 下载成功: {file_name} -> {dest_path}")
    return dest_path


def _task_path(task_info: TaskInfo) -> str:
    return f"{task_info.project}/{task_info.task}/"


def download_task_readme(task_info: TaskInfo, dest_dir: Optional[Path] = None) -> Path:
    """下载构建请求的自述文件

    Args:
        task_info:
        dest_dir:

    Returns:

    """
    if dest_dir is None:
        # 指向临时目录下的任务+时间戳解构目录
        dest_dir = config.TEMP_PATH / task_info.project / task_info.task
    dest_path = dest_dir / "README.md"

    download_file(task_info.commit_hash, task_info.readme_path(), dest_path)
    return dest_path


# 下载文件的类型：全部文件、uni资源包、readme、metadata、apk
FileType = Literal["all", "res", "readme", "metadata", "apk"]


def download_task_files(task_info: TaskInfo, file_type: FileType, dest_dir: Path = None) -> Path | None:
    """通过file_type下载任务中对应指定类型的文件

    Args:
        task_info: 任务信息
        file_type: 文件类型，字面量
        dest_dir: 目标目录
    """
    if dest_dir is None:
        # 指向临时目录下的任务+时间戳解构目录
        dest_dir = config.TEMP_PATH / task_info.project / task_info.task
    match file_type:
        case "all":
            download_task_all_files(task_info, dest_dir)
            # todo: 压缩返回压缩包
            return None
        case "res":
            return download_file(task_info.response_hash, task_info.res_path(), dest_dir / f"{task_info.task}.zip")
        case "readme":
            return download_task_readme(task_info, dest_dir)
        case "metadata":
            return download_file(task_info.response_hash, task_info.metadata_path(), dest_dir / "release-metadata.md")
        case "apk":
            return download_file(task_info.response_hash, task_info.apk_path(), dest_dir / task_info.apk_name())
    return None


def compare_readme_file(task_info: TaskInfo, readme_path: Path) -> bool:
    """比较当前任务的README是否与之前任务的readme相同，先下载资源包相同任务的 readme，然后进行文本比较"""
    origin_readme_path = download_task_readme(task_info)
    with open(origin_readme_path, "r", encoding="utf-8") as f1, open(readme_path, "r", encoding="utf-8") as f2:
        return f1.read() == f2.read()


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
    download_file(task_info.response_hash, task_info.metadata_path(), metadata_md)
    download_file(task_info.response_hash, task_info.obfuscated_path(), obfuscated_bak)
    download_file(task_info.response_hash, task_info.apk_path(), apk_file)
    return metadata_md, obfuscated_bak, apk_file


def download_task_all_files(task_info: TaskInfo, dest_dir: Path):
    target_task = dest_dir.name
    download_task_resp(task_info, dest_dir)
    download_file(task_info.response_hash, task_info.res_path(), dest_dir / f"{target_task}.zip")
    download_file(task_info.response_hash, task_info.readme_path(), dest_dir / "README.md")
