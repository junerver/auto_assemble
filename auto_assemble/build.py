import logging
import os
import shutil
import subprocess
from datetime import datetime

from auto_assemble.check_uni_base import check_uni_base
from auto_assemble.config import config
from auto_assemble.log import setup_logging
from auto_assemble.push import git_add, git_commit, get_staged_files


def get_build_output_name(release):
    """
    获取构建产物APK文件名
    Returns:
        str: APK文件名
    """
    # 查找构建输出目录下符合yyyyMMddHHmm格式的apk文件
    for file in os.listdir(
            config.BUILD_RELEASE_OUTPUT_DIR if release else config.BUILD_DEBUG_OUTPUT_DIR
    ):
        if file.endswith(".apk"):
            return file
    raise FileNotFoundError("未找到符合yyyyMMddHHmm格式的APK文件")


def get_distribution_target_dir(apk_name):
    """
    根据APK文件名生成目标目录
    Args:
        apk_name (str): APK文件名
    Returns:
        str: 目标目录路径
    """
    return os.path.join(config.DISTRIBUTION_PATH, config.PROD_DIR, apk_name.replace(".apk", ""))


def execute_gradle_build(release: bool = True):
    """
    执行gradle构建命令，默认构建 release 包
    Returns:
        bool: 构建是否成功
    """
    try:
        logging.info("开始执行gradle构建...")
        logging.info(f"当前工作目录: {os.getcwd()}")
        logging.info(f"目标项目目录: {config.ANDROID_UNI_BASE_PATH}")

        # 检查目录是否存在
        if not os.path.exists(config.ANDROID_UNI_BASE_PATH):
            logging.error(f"项目目录不存在: {config.ANDROID_UNI_BASE_PATH}")
            return False

        # 切换到项目目录
        os.chdir(config.ANDROID_UNI_BASE_PATH)
        logging.info(f"已切换到项目目录: {os.getcwd()}")

        # 检查 gradlew.bat 是否存在
        if not os.path.exists("gradlew.bat"):
            logging.error("gradlew.bat 文件不存在")
            return False

        # 执行gradle命令
        cmd = [
            "cmd",
            "/c",
            "gradlew.bat",
            "clean",
            f"app:assemble{"Release" if release else "Debug"}",
        ]
        logging.info(f"执行命令: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="gbk",
        )

        if result.returncode == 0:
            logging.info("Gradle构建成功")
            return True
        else:
            logging.error(f"Gradle构建失败: {result.stderr}")
            return False
    except Exception as e:
        logging.error(f"执行gradle构建时发生错误: {e}")
        return False


def copy_build_outputs(apk_name, target_dir, release) -> tuple[bool, str]:
    """
    复制构建产物到目标目录
    Returns:
        tuple<bool, str>: 复制是否成功, apk文件名(不包含尾缀)
    """
    try:
        # 确保目标目录存在
        os.makedirs(target_dir, exist_ok=True)

        # 复制APK文件
        source_apk = os.path.join(
            config.BUILD_RELEASE_OUTPUT_DIR if release else config.BUILD_DEBUG_OUTPUT_DIR, apk_name
        )
        target_apk = os.path.join(target_dir, apk_name)

        if os.path.exists(source_apk):
            shutil.copy2(source_apk, target_apk)
            logging.info(f"成功复制APK文件: {apk_name}")
        else:
            logging.error(f"源APK文件不存在: {source_apk}")
            return False, ""

        if release:
            # 复制metadata文件
            source_metadata = os.path.join(config.BUILD_RELEASE_OUTPUT_DIR, "release-metadata.md")
            target_metadata = os.path.join(target_dir, "release-metadata.md")

            if os.path.exists(source_metadata):
                shutil.copy2(source_metadata, target_metadata)
                logging.info("成功复制metadata文件")
            else:
                logging.error(f"源metadata文件不存在: {source_metadata}")
                return False, ""

        return True, apk_name.replace(".apk", "")
    except Exception as e:
        logging.error(f"复制构建产物时发生错误: {e}")
        return False, ""


def update_git_info(commit_message):
    """
    更新git信息，执行git add和git commit，commit message为"release_req: ${apk_name}"
    """
    try:
        # 切换到项目目录
        os.chdir(config.ANDROID_UNI_BASE_PATH)
        logging.info(f"已切换到项目目录: {os.getcwd()}")

        # 使用push.py中的git_add函数
        if not git_add(repo_path=config.ANDROID_UNI_BASE_PATH):
            logging.error("git add 执行失败")
            return False

        # 获取已暂存的文件
        staged_files = get_staged_files(repo_path=config.ANDROID_UNI_BASE_PATH)
        if not staged_files:
            logging.error("没有待提交的文件，资源文件未更新，终止执行")
            return False
        logging.info("待提交的文件列表:")
        for file in staged_files:
            logging.info(f"  - {file}")

        # 执行git commit
        if not git_commit(commit_message, repo_path=config.ANDROID_UNI_BASE_PATH):
            logging.error("git commit 执行失败")
            return False
        return True
    except Exception as e:
        logging.error(f"更新git信息时发生错误: {e}")
        return False


def main(target_dir: str = None, release: bool = True):
    """
    主函数：执行整个构建流程
    1. 配置日志系统
    2. 检查路径
    3. 执行gradle构建
    4. 复制构建产物

    Args:
        target_dir: 构建产物目标输出目录，可空，不传递时默认输出到分发目录下
        release: 指定构建类型，True 将构建release包，False 将构建debug包
    """
    try:
        # 配置日志
        setup_logging(task_name=f"新的构建任务 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logging.info("开始执行构建流程")

        # 检查基座工程
        check_uni_base()

        # 执行gradle构建
        if not execute_gradle_build(release):
            logging.error("Gradle构建失败，终止执行")
            return 1

        # 获取从release目录读取构建产物名称
        apk_name = get_build_output_name(release)
        # 没有传递时，指向分发目录
        if not target_dir:
            target_dir = get_distribution_target_dir(apk_name)
        # 复制构建产物，返回是否成功和apk文件名
        success, apk_name = copy_build_outputs(apk_name, target_dir, release)
        if not success:
            logging.error("复制构建产物失败，终止执行")
            return 1

        # 更新git信息，执行git add和git commit
        if not target_dir:
            # 来自分发的打包请求，附带提交打包请求的commit信息
            commit_message = f"release_req: {apk_name}{config.last_commit_message}"
        else:
            # 本地构建只记录变更时间
            commit_message = (
                f"{"release" if release else "debug"}: {datetime.now().strftime('%Y%m%d%H%M%S')}"
            )

        if not update_git_info(commit_message):
            logging.error("更新git信息失败，终止执行")
            return 1

        logging.info("所有操作执行成功")
        return 0
    except Exception as e:
        logging.error(f"执行过程中发生错误: {e}")
        return 1


if __name__ == "__main__":
    main()
