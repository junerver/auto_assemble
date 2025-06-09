import logging
import urllib.parse
from pathlib import Path
from typing import Optional

import requests

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

        response = requests.get(api_url, headers=headers, params=params, stream=True)
        response.raise_for_status()  # 自动抛出 4xx/5xx 错误
        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        logging.info(f"✅ 下载成功: {api_url} -> {dest_path}")
    except requests.RequestException as e:
        logging.error(f"❌ 下载失败\n原因: {e}")


def download_file(ref_hash: str, file_name: str, dest_path: Path):
    """
    对外暴露的下载文件函数
    Args:
        ref_hash:
        file_name:
        dest_path:

    Returns:

    """
    _download_gitlab_lfs_file(
        config.GITLAB_URL,
        config.ACCESS_TOKEN,
        config.PROJECT_ID,
        ref_hash,
        file_name,
        dest_path,
        True,
    )


def download_task_readme(task_info: TaskInfo, dest_dir: Optional[Path] = None) -> Path:
    """下载构建请求的自述文件

    Args:
        task_info:
        dest_dir:

    Returns:

    """
    if dest_dir is None:
        # 指向临时目录
        dest_dir = Path("/app") / "temp"

    download_file(task_info.commit_hash, "README.md", dest_dir / "README.md")
    return dest_dir


def compare_readme_file(task_info: TaskInfo, readme_path: Path) -> bool:
    """比较当前任务的README是否与之前任务的readme相同，先下载资源包相同任务的 readme，然后进行文本比较"""
    origin_readme_path = download_task_readme(task_info)
    with open(origin_readme_path, "r", encoding="utf-8") as f1, open(readme_path, "r", encoding="utf-8") as f2:
        return f1.read() == f2.read()


def download_task_resp(task_info: TaskInfo, dest_dir: Path):
    """下载构建响应文件到目标目录

    针对指定任务下载或创建构建响应文件：
    - md5值为名的空文件
    - README.md 构建自述
    - xxxx_obfuscated.bak 混淆后的资源文件（实际装载到壳工程的资源）
    - xxxx.apk 构建产物

    Args:
        task_info: 要下载的任务
        dest_dir: 目标目录

    """
    target_task = dest_dir.name
    md5_path = dest_dir / task_info.metadata.package_name
    md5_path.touch()
    download_file(task_info.commit_hash, "release-metadata.md", dest_dir / "release-metadata.md")
    download_file(task_info.commit_hash, f"{task_info.task}_obfuscated.bak", dest_dir / f"{target_task}_obfuscated.bak")
    download_file(task_info.commit_hash, f"{task_info.task}.apk", dest_dir / f"{target_task}.apk")


def download_task_all_files(task_info: TaskInfo, dest_dir: Path):
    target_task = dest_dir.name
    download_task_resp(task_info, dest_dir)
    download_file(task_info.commit_hash, f"{task_info.task}.zip", dest_dir / f"{target_task}.zip")
    download_file(task_info.commit_hash, "README.md", dest_dir / "README.md")
