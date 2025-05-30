import argparse
import json
import logging
import os
import shutil
import time
import zipfile
from datetime import datetime

from dotenv import load_dotenv
from win11toast import toast

from common.api import fetch_task_info
from common.commit_label import get_build_req_label
from common.log import setup_logging
from common.git import confirm_push, has_changes
from cbr.check_uni_project import check_uni_project, scan_uni_project
from cbr.create_readme_file import create_readme_file
from common.config import config
from common.git import (
    check_git_branch,
    get_staged_files,
    get_untracked_files,
    git_add,
    git_commit,
    git_push,
    sync_repository,
)
from common.types import TaskInfo


def create_build_req():
    """
    创建构建请求
    """
    try:
        setup_logging(True, "创建构建请求")
        parser = argparse.ArgumentParser(
            description="Load environment variables from a specified .env file and execute the program."
        )
        # 配置 UniApp 项目地址
        parser.add_argument("-u", "--uni", type=str, help="Path to the uniapp project root")
        # 提交消息参数，配置此参数时，通过cli模式运行，不需要用户确认
        parser.add_argument("-m", "--message", type=str, help="Commit message")
        # 构建模式参数
        parser.add_argument("-d", "--dev", action="store_true", help="Dev mode")
        parser.add_argument("-t", "--test", action="store_true", help="Test mode")
        parser.add_argument("-r", "--release", action="store_true", help="Release mode")
        args = parser.parse_args()

        env_file = os.path.join(os.getcwd(), ".env")
        if not os.path.exists(env_file):
            logging.error("没有找到.env文件，请检查是否存在")
            return 1
        load_dotenv(env_file)
        config.SERVER_HOST_URL = os.getenv("SERVER_HOST_URL")
        logging.info(f"打包服务器地址: {config.SERVER_HOST_URL}")

        # 默认打包模式为dev
        req_mode = "dev"
        if args.dev:
            req_mode = "dev"
        if args.test:
            req_mode = "test"
        if args.release:
            req_mode = "release"

        # 没有指定message，说明执行模式是ui模式
        commit_message = args.message

        if commit_message:
            config.work_mode = "cli"
        else:
            config.work_mode = "ui"
        # 如果指定了UniApp项目目录（即--uni ${projectDir}），则通过查询后台配置来进行项目配置
        if not args.uni:
            logging.error("没有执行UniApp项目路径，请追加 `--uni ${projectDir}`")
            return 1

        # 扫描uni项目，获取项目配置。此操作同时会赋值config.DISTRIBUTION_PATH
        try:
            env_vars, third_party_configs = scan_uni_project(args.uni, os.getcwd())
        except Exception as e:
            logging.error(f"扫描UniApp项目失败，请检查UniApp项目地址是否正确，错误信息：{e}")
            return 1

        is_ready, manifest_info, resources_dir = check_uni_project(env_vars, third_party_configs)
        if not is_ready:
            logging.error("本地资源文件校验失败，请检查HBX版本是否正确，产物输出目录是否正确！")
            return 1
        # 美观的打印manifest_info，但排除permissions字段
        manifest_info_without_permissions = manifest_info.copy()
        manifest_info_without_permissions.pop("permissions", {})
        manifest_info_without_permissions.pop("permissions_content", {})
        logging.info(f"manifest_info: {json.dumps(manifest_info_without_permissions, indent=4)}")

        # 更新UNI_APP_ID
        config.UNI_APP_ID = manifest_info["uniapp_id"]
        # 创建时间
        req_date = datetime.now().strftime("%Y%m%d%H%M")
        # 压缩资源目录下的名称为config.UNI_APP_ID的目录，并重命名为req_date.zip
        zip_file_path: str = os.path.join(resources_dir, f"{req_date}.zip")
        # 压缩资源目录下的名称为config.UNI_APP_ID的目录
        target_dir = os.path.join(resources_dir, config.UNI_APP_ID)
        if not os.path.exists(target_dir):
            logging.error(f"目录 {target_dir} 不存在")
            return 1
        # 压缩资源目录下的名称为config.UNI_APP_ID的目录
        with zipfile.ZipFile(zip_file_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(target_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.join(config.UNI_APP_ID, os.path.relpath(file_path, target_dir))
                    zipf.write(file_path, arcname)
        logging.info(f"已将 {target_dir} 目录压缩为 {zip_file_path}")

        # 检查配置路径是否有效
        if not config.DISTRIBUTION_PATH:
            logging.error("配置错误: DISTRIBUTION_PATH 未设置或为空")
            return 1
        if not config.PROD_NAME:
            logging.error("配置错误: PROD_NAME 未设置或为空")
            return 1

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
        req_date_dir = os.path.join(config.DISTRIBUTION_PATH, config.PROD_NAME, req_date)
        config.cur_task_id = f"{config.PROD_NAME},{req_date}"
        config.cur_task_dir = req_date_dir
        logging.info(f"本次请求id:{config.cur_task_id}")
        os.makedirs(req_date_dir, exist_ok=True)
        # 复制zip文件到指定目录
        shutil.copy(zip_file_path, str(req_date_dir))
        os.remove(zip_file_path)
        logging.info(f"本次请求的资源文件已压缩为{zip_file_path}，并已复制到{req_date_dir}目录下")
        create_readme_file(str(req_date_dir), manifest_info)
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
        if config.work_mode == "ui":
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
    except Exception as e:
        logging.error(f"创建构建请求时发生错误: {str(e)}")
        import traceback

        logging.error(f"错误详情: {traceback.format_exc()}")
        return 1


def rolling_req_build_status():
    """
    轮询请求构建主机，获取构建状态，toast通知成功、失败
    """
    dots = ""  # 用于存储进度点
    should_exit = True
    while not should_exit:
        try:

            def on_success(task_info: TaskInfo):
                nonlocal should_exit, dots
                status = task_info.status

                if status == "running":
                    dots = dots + "." if len(dots) < 30 else "."
                    logging.info(f"打包中{dots}")
                    time.sleep(5)  # 等待5秒后继续轮询
                    should_exit = False
                elif status in ["completed", "failed"]:
                    # 简化版的toast提示
                    success = status == "completed"
                    status_text = "✅成功" if success else "❌失败"
                    logging.info("打包完毕，正在同步本地仓库....")
                    if success:
                        sync_repository(config.DISTRIBUTION_PATH)
                    message = f"🗃️项目: {task_info.project}\n🏗️任务: {task_info.task}"
                    if success:
                        buttons = [
                            {
                                "activationType": "protocol",
                                "arguments": f"file:///{config.cur_task_dir.replace('\\', '/')}",
                                "content": "打开目录",
                            }
                        ]
                        toast(f"🎉构建结果:{status_text}", message, buttons=buttons)
                    else:
                        toast(f"🔦构建结果:{status_text}", message, button="我知道了！")
                    should_exit = True

            def on_error():
                nonlocal should_exit
                logging.info("尚未查询到任务状态，请稍等...")
                time.sleep(5)  # 等待5秒后继续轮询
                should_exit = False

            fetch_task_info(config.cur_task_id, on_success, on_error)
        except Exception as e:
            logging.error(f"轮询任务状态时发生错误: {str(e)}")
            break


def check_git_lfs_installed(repo_path=".") -> bool:
    """
    检查git lfs是否安装，检查.git/hooks目录下的pre-push文件是否存在git-lfs
    """
    hooks_path = os.path.join(repo_path, ".git", "hooks")
    pre_push_hook = os.path.join(hooks_path, "pre-push")
    if os.path.exists(pre_push_hook):
        with open(pre_push_hook, "r") as f:
            content = f.read()
            if "git-lfs" in content:
                return True
    return False


if __name__ == "__main__":
    create_build_req()
    pass
