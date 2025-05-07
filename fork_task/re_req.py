import logging
import os
import shutil

from auto_assemble.error import BusinessException
from auto_assemble.git import check_git_branch
from auto_assemble.git import git_add, git_commit, git_push
from fork_task.config import DISTRIBUTION_PATH


def re_req(temp_dir: str, fork_task_info: dict) -> None:
    """
    重新请求派生任务
    """
    # 确保使用正确的路径分隔符
    temp_dir = os.path.normpath(temp_dir)
    target_branch = fork_task_info["target_branch"]
    target_task_id = fork_task_info["id"]
    commit_message = fork_task_info["commit_message"]
    prod_name, target_task = target_task_id.split(",")
    logging.info(f"切换到的目标分支：{DISTRIBUTION_PATH}/{target_branch}")
    check_git_branch(DISTRIBUTION_PATH, target_branch)
    # 创建派生任务目录
    target_dir = os.path.join(DISTRIBUTION_PATH, prod_name, target_task)
    os.makedirs(target_dir, exist_ok=True)
    # 拷贝临时目录中的 zip 文件和 readme.md 文件到派生任务目录
    zip_file = os.path.join(temp_dir, f"{target_task}.zip")
    readme_file = os.path.join(temp_dir, "README.md")
    shutil.copy(zip_file, target_dir)
    shutil.copy(readme_file, target_dir)
    logging.info(f"拷贝临时目录中的 zip 文件和 readme.md 文件到派生任务目录: {target_dir}")

    # git add ,commit,push
    if not git_add(repo_path=DISTRIBUTION_PATH):
        raise BusinessException(13004)
    if not git_commit(commit_message, repo_path=DISTRIBUTION_PATH):
        raise BusinessException(13005)
    if not git_push(repo_path=DISTRIBUTION_PATH):
        raise BusinessException(13006)
    logging.info(f"派生任务 {target_task_id} 重新请求成功")
    shutil.rmtree(os.path.abspath(temp_dir))
