import argparse
import json
import logging
import os
import time
import zipfile
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from win11toast import toast

from cbr.submit_cbr import cbr_by_repo, CommitRepoConfig, cbr_by_post
from common.api import fetch_task_info
from common.log import setup_logging
from cbr.check_uni_project import check_uni_project, scan_uni_project
from common.config import config
from common.git import (
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

        env_file: Path = Path.cwd() / ".env"
        if not env_file.exists():
            logging.error("没有找到.env文件，请检查是否存在")
            return 1
        load_dotenv(env_file)
        config.SERVER_HOST_URL = os.getenv("SERVER_HOST_URL")
        if os.getenv("CBR_MODE"):
            cbr_mode = os.getenv("CBR_MODE")
            if cbr_mode not in ["repo", "post"]:
                logging.error("CBR_MODE 配置错误，只支持`repo`、`post`两种模式，请检查")
                return 1
            config.cbr_mode = cbr_mode
        else:
            config.cbr_mode = "repo"

        logging.info(f"打包服务器地址: {config.SERVER_HOST_URL}")
        logging.info(f"CBR_MODE: {config.cbr_mode}")

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
            env_vars, third_party_configs = scan_uni_project(Path(args.uni), Path.cwd())
        except Exception as e:
            logging.exception(f"扫描UniApp项目失败，请检查UniApp项目地址是否正确，错误信息：{e}")
            return 1

        check_result = check_uni_project(env_vars, third_party_configs)
        if check_result is None:
            logging.error("本地资源文件校验失败，请检查HBX版本是否正确，产物输出目录是否正确！")
            return 1
        manifest_info, resources_dir = check_result
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
        zip_file_path: Path = resources_dir / f"{req_date}.zip"
        # 压缩资源目录下的名称为config.UNI_APP_ID的目录
        target_dir = resources_dir / config.UNI_APP_ID
        if not target_dir.exists():
            logging.error(f"目录 {target_dir} 不存在")
            return 1
        # 压缩资源目录下的名称为config.UNI_APP_ID的目录
        with zipfile.ZipFile(zip_file_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file_path in target_dir.rglob("*"):
                if file_path.is_file():
                    arcname = Path(config.UNI_APP_ID) / file_path.relative_to(target_dir)
                    zipf.write(file_path, arcname)
        logging.info(f"已将 {target_dir} 目录压缩为 {zip_file_path}")

        # 检查配置路径是否有效
        if not config.DISTRIBUTION_PATH:
            logging.error("配置错误: DISTRIBUTION_PATH 未设置或为空")
            return 1
        if not config.PROD_NAME:
            logging.error("配置错误: PROD_NAME 未设置或为空")
            return 1

        # 配置当前任务id
        config.cur_task_id = f"{config.PROD_NAME},{req_date}"
        logging.info(f"本次请求id:{config.cur_task_id} [${config.cbr_mode}]")
        # 根据模式不同这只不同的cbr方式
        if config.cbr_mode == "repo":
            # 操作repo仓库提交cbr请求
            return cbr_by_repo(
                CommitRepoConfig(
                    req_date=req_date,
                    req_mode=req_mode,
                    zip_file_path=zip_file_path,
                    manifest_info=manifest_info,
                )
            )
        else:
            # 提交网络请求，通过服务器cbr接口
            return cbr_by_post(
                CommitRepoConfig(
                    req_date=req_date,
                    req_mode=req_mode,
                    zip_file_path=zip_file_path,
                    manifest_info=manifest_info,
                )
            )

    except Exception as e:
        logging.exception(f"创建构建请求时发生错误: {str(e)}")
        return 1


def rolling_req_build_status():
    """
    轮询请求构建主机，获取构建状态，toast通知成功、失败
    """
    dots = ""  # 用于存储进度点
    should_exit = False  # 修改为 False，确保循环至少执行一次
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
                                "arguments": f"file:///{str(config.cur_task_dir).replace('\\', '/')}",
                                "content": "打开目录",
                            }
                        ]
                        toast(f"🎉构建结果:{status_text}", message, buttons=buttons)
                    else:
                        toast(f"🔦构建结果:{status_text}", message, button="我知道了！")
                    should_exit = True

            def on_error(_: str):
                nonlocal should_exit
                logging.info("尚未查询到任务状态，请稍等...")
                time.sleep(5)  # 等待5秒后继续轮询
                should_exit = False

            fetch_task_info(config.cur_task_id, on_success, on_error)
        except Exception as e:
            logging.exception(f"轮询任务状态时发生错误: {str(e)}")
            break


def check_git_lfs_installed(repo_path: str) -> bool:
    """
    检查git lfs是否安装，检查.git/hooks目录下的pre-push文件是否存在git-lfs
    """
    hooks_path = Path(repo_path) / ".git" / "hooks"
    pre_push_hook = hooks_path / "pre-push"
    if pre_push_hook.exists():
        with open(pre_push_hook, "r") as f:
            content = f.read()
            if "git-lfs" in content:
                return True
    return False


if __name__ == "__main__":
    create_build_req()
    pass
