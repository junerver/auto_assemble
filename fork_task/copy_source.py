import json
import logging
from pathlib import Path

import requests

from common.api import fetch_task_info
from common.gitlab import download_file
from common.error import BusinessException
from common.extract import modern_extract
from common.types import TaskInfo
from fork_task.config import SERVER_HOST_URL


def copy_source(fork_task_id: str) -> tuple[Path, dict]:
    """
    复制源文件到目标文件，首先需要请求 /api/fork-task/<fork_task_id> ，获取派生任务详情。
    从派生任务详情中获取源分支、项目id、目标分支、项目id。
    然后拷贝源中的 zip 文件和 readme.md 文件到临时目录，并执行解压。
    返回临时目录和派生任务详情。
    """

    # 请求 /api/fork-task/<fork_task_id> ，获取派生任务详情
    logging.info(f"请求派生任务详情: {f'{SERVER_HOST_URL}/api/fork_task/{fork_task_id}'}")
    response = requests.get(f"{SERVER_HOST_URL}/api/fork_task/{fork_task_id}")
    if response.status_code != 200:
        raise BusinessException(13001)
    fork_task_info = response.json()["fork_task"]
    logging.info(f"派生任务详情: {json.dumps(fork_task_info, indent=4)}")
    # 源分支、项目id
    source_task_id: str = fork_task_info["source_task_id"]
    _, source_task_timestamp = source_task_id.split(",")
    # 派生的任务目标分支、项目id
    target_task_id = fork_task_info["id"]
    # 派生任务的临时目录
    _, target_task = target_task_id.split(",")
    # 拷贝zip文件\readme.md文件到临时目录
    temp_dir: Path = Path("/app") / "temp" / target_task
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_zip_path: Path = temp_dir / f"{source_task_timestamp}.zip"
    temp_md_path: Path = temp_dir / "README.md"

    def on_success(task_info: TaskInfo):
        logging.info(f"源任务详情: {task_info.to_json()}")
        source_zip_url = f"{task_info.project}/{task_info.task}/{source_task_timestamp}.zip"
        source_md_url = f"{task_info.project}/{task_info.task}/README.md"
        # 下载文件
        download_file(task_info.commit_hash, source_zip_url, temp_zip_path)
        download_file(task_info.commit_hash, source_md_url, temp_md_path)

    fetch_task_info(source_task_id, on_success, None)

    # 解压缩zip文件
    temp_extract_dir: Path = temp_dir / "extract"
    modern_extract(temp_zip_path, outdir=temp_extract_dir)
    logging.info(f"解压zip文件到临时目录: {temp_extract_dir}")

    temp_zip_path.unlink()
    logging.info(f"删除zip文件: {temp_zip_path}")

    return temp_dir, fork_task_info


if __name__ == "__main__":
    task_id = "identify_field,202505281803"
    copy_source(task_id)
