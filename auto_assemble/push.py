import logging
import os
import re
import subprocess
from datetime import datetime

from auto_assemble.config import config
from auto_assemble.git import get_untracked_files, get_staged_files, git_commit, git_add, git_push
from auto_assemble.log import setup_logging


def validate_timestamp_format(timestamp) -> bool:
    """验证时间戳格式是否为yyyyMMddHHmm"""
    pattern = r"^\d{12}$"
    if not re.match(pattern, timestamp):
        return False
    try:
        datetime.strptime(timestamp, "%Y%m%d%H%M")
        return True
    except ValueError:
        return False


def has_changes(cwd=config.DISTRIBUTION_PATH) -> bool:
    """检查是否有任何修改（包括未跟踪和已修改的文件）"""
    try:
        # 检查未跟踪的文件
        result = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            capture_output=True,
            text=True,
            cwd=cwd,
        )
        if result.returncode != 0:
            logging.error("获取未跟踪文件列表失败")
            return False

        # 检查已修改的文件
        modified_result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=cwd,
        )
        if modified_result.returncode != 0:
            logging.error("获取git状态失败")
            return False

        # 如果有未跟踪的文件或已修改的文件，返回True
        return bool(result.stdout.strip()) or bool(modified_result.stdout.strip())
    except Exception as e:
        logging.error(f"检查git状态时发生错误: {str(e)}")
        return False


def validate_files(files):
    """验证文件是否符合要求"""
    apk_file = None
    metadata_file = None

    for file in files:
        # 统一使用正斜杠处理路径
        file = file.replace("\\", "/")
        file_name = file.split("/")[-1]
        if file_name.endswith(".apk"):
            apk_file = file
        elif file_name == "release-metadata.md":
            metadata_file = file

    if not apk_file or not metadata_file:
        logging.error("缺少必要的文件：需要.apk文件和release-metadata.md文件")
        return False, None

    # 获取目录名（时间戳）
    # 从完整路径中提取时间戳部分
    path_parts = apk_file.split("/")
    if len(path_parts) < 2:
        logging.error(f"文件路径格式不正确: {apk_file}")
        return False, None

    timestamp = path_parts[-2]  # 获取倒数第二个部分作为时间戳
    if not validate_timestamp_format(timestamp):
        logging.error(f"目录名格式不正确: {timestamp}")
        return False, None

    # 验证apk文件名是否与目录名一致
    apk_name = path_parts[-1]  # 使用已经分割好的路径部分
    if not apk_name.startswith(timestamp):
        logging.error(f"APK文件名与目录名不匹配: {apk_name} vs {timestamp}")
        return False, None

    return True, timestamp


def get_modified_apk():
    """获取已修改的apk文件"""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=config.DISTRIBUTION_PATH,
        )
        if result.returncode != 0:
            logging.error("获取git状态失败")
            return None

        for line in result.stdout.splitlines():
            if line.endswith(".apk"):
                # 获取文件名（去掉状态标记和空格）
                file_path = line[3:].strip()
                # 统一使用正斜杠处理路径
                file_path = file_path.replace("\\", "/")
                # 获取文件名（不含路径）
                file_name = file_path.split("/")[-1]
                # 验证文件名格式
                if validate_timestamp_format(file_name.replace(".apk", "")):
                    return file_name.replace(".apk", "")
        return None
    except Exception as e:
        logging.error(f"获取已修改的apk文件时发生错误: {str(e)}")
        return None


def confirm_push(staged_files, commit_message):
    """确认是否推送"""
    logging.info("=" * 50)
    logging.info("推送确认")
    logging.info("=" * 50)
    logging.info("本次提交的文件:")
    for file in staged_files:
        logging.info(f"  - {file}")
    logging.info(f"提交信息: {commit_message}")
    logging.info("=" * 50)

    if config.work_mode == "ui":
        user_input = input("\n是否推送本次提交？(Y/y 确认，直接回车取消): ").strip()
        return user_input.lower() == "y"
    else:
        return True


def main():
    """主函数"""
    try:
        # 配置日志
        setup_logging(task_name=f"校验分发提交 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logging.info("开始执行git推送流程")

        # 检查目录是否存在
        if not os.path.exists(config.DISTRIBUTION_PATH):
            logging.error(f"目录不存在: {config.DISTRIBUTION_PATH}")
            return 11001

        # 检查是否有任何修改
        if not has_changes():
            logging.info("没有需要提交的修改")
            return 11006

        # 获取未跟踪的文件
        untracked_files = get_untracked_files(config.DISTRIBUTION_PATH)
        if untracked_files:
            logging.info(f"发现{len(untracked_files)}个未跟踪的文件")
            # 验证文件
            is_valid, timestamp = validate_files(untracked_files)
            if not is_valid:
                return 11007
        else:
            logging.info("没有未跟踪的文件，继续检查已修改的文件")
            # 获取已修改的apk文件
            timestamp = get_modified_apk()
            if not timestamp:
                logging.error("未找到符合格式的已修改apk文件")
                return 11008

        # 执行git add
        if not git_add(repo_path=config.DISTRIBUTION_PATH):
            return 11009

        # 获取已暂存的文件并验证
        staged_files = get_staged_files(repo_path=config.DISTRIBUTION_PATH)
        if not staged_files:
            logging.error("没有待提交的文件")
            return 11010

        logging.info("待提交的文件列表:")
        for file in staged_files:
            logging.info(f"  - {file}")

        is_valid, _ = validate_files(staged_files)
        if not is_valid:
            logging.error("待提交的文件不符合要求")
            return 11011

        # todo 执行git commit，提交消息需要完善
        from auto_assemble.build import get_build_resp_message

        commit_message = get_build_resp_message(f"{timestamp} 打包")
        if not git_commit(commit_message, config.DISTRIBUTION_PATH):
            return 11012

        # 确认是否推送
        if not confirm_push(staged_files, commit_message):
            logging.info("用户取消推送")
            return 11013

        # 执行git push
        if not git_push(repo_path=config.DISTRIBUTION_PATH):
            return 11014

        logging.info("所有操作执行成功")
        return 0
    except Exception as e:
        logging.error(f"执行过程中发生错误: {e}")
        return 1


if __name__ == "__main__":
    main()
