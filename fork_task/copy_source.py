import json
import logging
import os
import shutil

import patoolib
import requests

from common.error import BusinessException
from common.git import check_git_branch
from fork_task.config import SERVER_HOST_URL, DISTRIBUTION_PATH


def copy_source(fork_task_id: str) -> tuple[str, dict]:
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
    source_branch = fork_task_info["source_branch"]
    source_task_id = fork_task_info["source_task_id"]
    # 派生的任务目标分支、项目id
    # target_branch = fork_task_info["target_branch"]
    target_task_id = fork_task_info["id"]
    # 派生任务的临时目录
    _, target_task = target_task_id.split(",")

    logging.info(f"切换到的源分支：{DISTRIBUTION_PATH}/{source_branch}")
    check_git_branch(DISTRIBUTION_PATH, source_branch)
    # 校验源任务指向的目录是否存在，source_task既是任务目录，也是任务资源zip名
    prod_name, source_task = source_task_id.split(",")
    source_dir = os.path.join(DISTRIBUTION_PATH, prod_name, source_task)
    if not os.path.exists(source_dir):
        raise BusinessException(13002)
    # 提取源任务目录中的 task_dir.zip 文件、README.md 文件
    zip_file = os.path.join(source_dir, f"{source_task}.zip")
    readme_file = os.path.join(source_dir, "README.md")
    if not os.path.exists(zip_file) or not os.path.exists(readme_file):
        raise BusinessException(13003)
    logging.info(f"源任务目录：{source_dir}\nzip文件：{zip_file}\nreadme文件：{readme_file}")
    # 拷贝zip文件\readme.md文件到临时目录
    temp_dir = os.path.join("/app", "temp", target_task)
    os.makedirs(temp_dir, exist_ok=True)
    shutil.copy(zip_file, temp_dir)
    shutil.copy(readme_file, temp_dir)
    logging.info(f"复制源文件到临时目录: {temp_dir}")

    # 解压缩zip文件
    temp_extract_dir = os.path.join(temp_dir, "extract")
    patoolib.extract_archive(zip_file, outdir=temp_extract_dir)
    logging.info(f"解压zip文件到临时目录: {temp_extract_dir}")

    # 删除 zip 文件
    temp_zip_file = os.path.join(temp_dir, f"{source_task}.zip")
    os.remove(temp_zip_file)
    logging.info(f"删除zip文件: {temp_zip_file}")

    return temp_dir, fork_task_info
