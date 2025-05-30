import logging
import urllib.parse
from pathlib import Path

import requests

from common.config import config


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
