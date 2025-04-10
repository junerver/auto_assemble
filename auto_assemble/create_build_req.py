import argparse
import json
import logging
import os
import shutil
import time
import zipfile
from datetime import datetime
from textwrap import dedent

import requests
from dotenv import load_dotenv
from win11toast import toast

from auto_assemble.build import get_build_req_label
from auto_assemble.check_uni_project import check_uni_project
from auto_assemble.config import config
from auto_assemble.create_env_file import check_and_create_env
from auto_assemble.git import (
    check_git_branch,
    get_staged_files,
    get_untracked_files,
    git_add,
    git_commit,
    git_push,
    sync_repository,
)
from auto_assemble.log import setup_logging
from auto_assemble.push import confirm_push, has_changes


def create_readme_file(req_dir: str, manifest_info: dict):
    """
    创建readme.txt文件
    Args:
        req_dir: 请求目录路径
        manifest_info: manifest.json解析信息
    """
    readme_file_path = os.path.join(req_dir, "README.md")
    with open(readme_file_path, "w", encoding="utf-8") as f:
        # 写入标题和基本要求
        f.write(
            dedent(
                """\
            # 打包要求

            1. 打包使用的 HBuilderX 版本号，必须使用 4.45 以上

               HBuilderX 版本：`{hbx_version}`

            2. Uniapp 打包后的资源包

            3. Uniapp App ID：`{uniapp_id}`

            4. Uniapp App key：`{uniapp_key}`

            5. AbiFilters：`{abi_filters}`

            6. UrlSchemes：`{schemes}`

            7. manifest.json 中配置的版本名称 versionName、版本号 versionCode

               版本名称 versionName：`{version_name}`

               版本号 versionCode：`{version_code}`

            8. 提供 Android 基座需要添加、移除的权限列表，基座默认权限如下：

            {permissions_content}
        """
            ).format(
                hbx_version=manifest_info["hbx_version"],
                uniapp_id=manifest_info["uniapp_id"],
                uniapp_key=manifest_info["uniapp_key"],
                abi_filters=manifest_info["abi_filters"],
                schemes=manifest_info["schemes"],
                version_name=manifest_info["version_name"],
                version_code=manifest_info["version_code"],
                permissions_content=manifest_info["permissions_content"],
            )
        )
        # 写入模块信息
        if manifest_info["modules"]:
            f.write("9. 模块信息：\n\n")
            for module in manifest_info["modules"]:
                f.write(f"    > - {module}\n")

        # 写入第三方配置
        if manifest_info["third_party_config"]:
            third_party_config_text = ""
            for platform, config in manifest_info["third_party_config"].items():
                third_party_config_text += f"               {platform}:\n"
                for key, value in config.items():
                    third_party_config_text += f"                 {key}: {value}\n"

            f.write(
                dedent(
                    f"""
               10. 第三方平台配置信息：

               ```yml
{third_party_config_text}               ```
            """
                )
            )

        logging.info(f"已创建README.md文件：{readme_file_path}")


def create_build_req():
    """
    创建构建请求
    """
    try:
        parser = argparse.ArgumentParser(
            description="Load environment variables from a specified .env file and execute the program."
        )
        # 指定.env文件路径
        parser.add_argument("--env", type=str, help="Path to the .env file")
        parser.add_argument("-m", "--message", type=str, help="Commit message")
        parser.add_argument("-d", "--dev", action="store_true", help="Dev mode")
        parser.add_argument("-t", "--test", action="store_true", help="Test mode")
        parser.add_argument("-r", "--release", action="store_true", help="Release mode")
        args = parser.parse_args()

        # 默认打包模式为dev
        req_mode = "dev"
        if args.dev:
            req_mode = "dev"
        if args.test:
            req_mode = "test"
        if args.release:
            req_mode = "release"

        env_file = args.env if args.env else os.path.join(os.getcwd(), ".env")
        # 没有指定message，说明执行模式是ui模式
        commit_message = args.message

        if commit_message:
            config.work_mode = "cli"
        else:
            config.work_mode = "ui"

        setup_logging(True, "创建构建请求")
        check_and_create_env(env_file, "4")

        # 加载指定的 .env 文件
        load_dotenv(env_file)

        is_ready, manifest_info, resources_dir = check_uni_project()
        if not is_ready:
            logging.error("本地资源文件校验失败")
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
        zip_file_path = os.path.join(resources_dir, f"{req_date}.zip")
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
                    arcname = os.path.join(
                        config.UNI_APP_ID, os.path.relpath(file_path, target_dir)
                    )
                    zipf.write(file_path, arcname)
        logging.info(f"已将 {target_dir} 目录压缩为 {zip_file_path}")

        # 检查配置路径是否有效
        if not config.DISTRIBUTION_PATH:
            logging.error("配置错误: DISTRIBUTION_PATH 未设置或为空")
            return 1
        if not config.PROD_NAME:
            logging.error("配置错误: PROD_NAME 未设置或为空")
            return 1
        # 同步仓库
        if not sync_repository(config.DISTRIBUTION_PATH):
            logging.error("Git仓库同步失败，终止执行")
            return 1
        if req_mode == "dev":
            check_git_branch(config.DISTRIBUTION_PATH, "master")
        else:
            check_git_branch(config.DISTRIBUTION_PATH, req_mode)

        # 在分发目录的PROD_NAME目录下创建req_date目录
        req_date_dir = os.path.join(config.DISTRIBUTION_PATH, config.PROD_NAME, req_date)
        config.cur_task_id = f"{config.PROD_NAME},{req_date}"
        config.cur_task_dir = req_date_dir
        logging.info(f"本次请求id:{config.cur_task_id}")
        os.makedirs(req_date_dir, exist_ok=True)
        # 复制zip文件到指定目录
        shutil.copy(zip_file_path, req_date_dir)
        os.remove(zip_file_path)
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
        if config.work_mode == "ui":
            commit_message = input("请输入提交信息：")

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
    while True:
        try:
            response = requests.get(f"http://192.168.172.110:5005/task/{config.cur_task_id}")
            if response.status_code == 200:
                task_info = response.json().get("task", {})
                status = task_info.get("status")

                if status == "running":
                    dots = dots + "." if len(dots) < 30 else "."
                    logging.info(f"打包中{dots}")
                    time.sleep(5)  # 等待5秒后继续轮询
                    continue
                elif status in ["completed", "failed"]:
                    # 简化版的toast提示
                    success = status == "completed"
                    status_text = "✅成功" if success else "❌失败"
                    logging.info("打包完毕，正在同步本地仓库....")
                    if success:
                        sync_repository(config.DISTRIBUTION_PATH)
                    message = f"🗃️项目: {task_info.get('project_name', '')}\n🏗️任务: {task_info.get('task_name', '')}"
                    if success:
                        buttons = [
                            {
                                "activationType": "protocol",
                                "arguments": f'file:///{config.cur_task_dir.replace("\\", "/")}',
                                "content": "打开目录",
                            }
                        ]
                        toast(f"🎉构建结果:{status_text}", message, buttons=buttons)
                    else:
                        toast(f"🎉构建结果:{status_text}", message, button="我知道了！")

                    break
            else:
                logging.error(f"获取任务状态失败: {response.status_code}")
                break
        except Exception as e:
            logging.error(f"轮询任务状态时发生错误: {str(e)}")
            break


if __name__ == "__main__":
    create_build_req()
    time.sleep(5)  # 等待5秒后开始轮询
    rolling_req_build_status()
    if config.work_mode == "ui":
        input("按回车键退出")
