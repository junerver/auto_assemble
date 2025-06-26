import logging
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from dataclasses_json import DataClassJsonMixin

from cbr.create_build_req import check_git_lfs_installed
from cbr.create_readme_file import create_readme_file
from common.api import submit_cbr_form
from common.commit_label import get_build_req_label
from common.config import config
from common.git import (
    get_untracked_files,
    get_staged_files,
    git_add,
    git_commit,
    confirm_push,
    git_push,
    has_changes,
    sync_repository,
    check_git_branch,
)
from common.types import ManifestInfo


@dataclass
class CommitRepoConfig(DataClassJsonMixin):
    # 请求提交时间戳
    req_date: str
    # 请求模式：dev、test、release
    req_mode: str
    # 在uni项目压缩后的zip包位置
    zip_file_path: Path
    # 解析Uni项目后的Manifest信息
    manifest_info: ManifestInfo


def cbr_by_repo(commit_config: CommitRepoConfig) -> int:
    """
    将产物提交到分发仓库，并执行推送
    Returns:

    """
    req_date = commit_config.req_date
    req_mode = commit_config.req_mode
    zip_file_path = commit_config.zip_file_path
    manifest_info = commit_config.manifest_info

    # 检查lfs是否正确配置，否则阻止执行
    if not check_git_lfs_installed(config.DISTRIBUTION_PATH):
        logging.error(
            r"Git LFS未正确配置，请先以管理员身份运行PowerShell进入仓库根目录下，执行命令：.\.build_req\git-lfs.ps1"
        )
        return 1

    # 同步仓库
    if not sync_repository(config.DISTRIBUTION_PATH):
        logging.error("Git仓库同步失败，终止执行")
        return 1

    target_branch = "master" if req_mode == "dev" else req_mode
    if not check_git_branch(config.DISTRIBUTION_PATH, target_branch):
        logging.error("Git切换失败，终止执行")
        return 1

    # 在分发目录的PROD_NAME目录下创建req_date目录
    req_date_dir: Path = Path(config.DISTRIBUTION_PATH) / config.PROD_NAME / req_date
    config.cur_task_dir = req_date_dir.resolve()
    req_date_dir.mkdir(parents=True, exist_ok=True)
    # 复制zip文件到指定目录
    shutil.copy(zip_file_path, str(req_date_dir))
    zip_file_path.unlink()
    logging.info(f"本次请求的资源文件已压缩为{zip_file_path}，并已复制到{req_date_dir}目录下")
    create_readme_file(req_date_dir, manifest_info)
    # 在分发目录执行git add
    os.chdir(config.DISTRIBUTION_PATH)
    # 检查是否有任何修改
    if not has_changes():
        logging.info("没有需要提交的修改")
        return 1

    # 获取未跟踪的文件
    untracked_files = get_untracked_files(config.DISTRIBUTION_PATH)
    if not untracked_files:
        logging.info("没有未跟踪的文件，继续检查已修改的文件")
        # 获取已修改的文件
        staged_files = get_staged_files(repo_path=config.DISTRIBUTION_PATH)
        if not staged_files:
            logging.error("没有待提交的文件")
            return 1
    else:
        # 执行git add
        if not git_add(repo_path=config.DISTRIBUTION_PATH):
            return 1
        # 获取已暂存的文件
        staged_files = get_staged_files(repo_path=config.DISTRIBUTION_PATH)
        if not staged_files:
            logging.error("没有待提交的文件")
            return 1

    logging.info("待提交的文件列表:")
    for file in staged_files:
        logging.info(f"  - {file}")
    # 执行git commit
    commit_message = ""
    # 关闭cli -m 传递提交信息方式，强制使用交互式模式，用户输入信息
    if True:
        # 如果通过ui模式运行，则需要用户输入提交信息，必须输入内容
        while True:
            commit_message = input("请输入提交信息：")
            if commit_message:
                break
            else:
                logging.error("提交信息不能为空")

    commit_message = get_build_req_label(req_mode) + commit_message
    logging.info(f"提交信息：{commit_message}")
    if not git_commit(commit_message, config.DISTRIBUTION_PATH):
        return 1

    # 确认是否推送，推送消息中追加构建模式的标识
    if not confirm_push(staged_files, commit_message):
        logging.info("用户取消推送")
        return 1

    # 执行git push
    if not git_push(repo_path=config.DISTRIBUTION_PATH):
        return 1
    logging.info("打包请求已提交，请稍等...")
    return 0


def cbr_by_post(commit_config: CommitRepoConfig):
    """
    通过提交接口请求创建cbr请求
    Returns:

    """
    req_date = commit_config.req_date
    req_mode = commit_config.req_mode
    zip_file_path = commit_config.zip_file_path
    manifest_info = commit_config.manifest_info

    # 在线提交cbr请求时避免将文件传递到分发目录，而是先放置到临时目录下
    temp_dir_path: Path = Path(config.DISTRIBUTION_PATH) / ".build_req" / "temp" / config.PROD_NAME / req_date
    temp_dir_path.mkdir(parents=True, exist_ok=True)
    readme_path = create_readme_file(temp_dir_path, manifest_info)
    # 暂存工作目录，用于后续toast定位
    config.cur_task_dir = temp_dir_path
    # 复制zip文件到指定目录
    shutil.copy(zip_file_path, str(temp_dir_path))
    commit_message = ""
    # 关闭cli -m 传递提交信息方式，强制使用交互式模式，用户输入信息
    if True:
        # 如果通过ui模式运行，则需要用户输入提交信息，必须输入内容
        while True:
            commit_message = input("请输入提交信息：")
            if commit_message:
                break
            else:
                logging.error("提交信息不能为空")

    commit_message = get_build_req_label(req_mode) + commit_message
    logging.info(f"提交信息：{commit_message}")
    # 确认是否推送，推送消息中追加构建模式的标识
    if not confirm_push([zip_file_path.name, readme_path.name], commit_message):
        logging.info("用户取消推送")
        return 1

    if not submit_cbr_form(config.PROD_NAME, config.current_author, commit_message, readme_path, zip_file_path):
        logging.error("提交cbr请求失败")
        return 1

    return 0


def clear_temp_dir():
    """
    清理临时目录
    Returns:

    """
    temp_dir_path: Path = Path(config.DISTRIBUTION_PATH) / ".build_req" / "temp"
    if temp_dir_path.exists():
        shutil.rmtree(temp_dir_path)
        logging.info(f"清理临时目录{temp_dir_path}成功")
