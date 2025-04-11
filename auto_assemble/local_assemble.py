import logging
import os
from datetime import datetime

from auto_assemble.config import config
from auto_assemble.copy_res import check_apps_directory, clear_directory, extract_compressed_file
from auto_assemble.git import check_git_branch
from auto_assemble.log import setup_logging
from auto_assemble.update_android_manifest import update_android_manifest
from auto_assemble.update_build_gradle import update_build_gradle
from auto_assemble.update_control_file import update_control_file
from cbr.check_uni_project import check_uni_project


def local_copy_res(release):
    """
    本地资源拷贝：
    1. 校验设置的资源路径
    2. 从项目中的 manifest.json 文件中读取信息
    3. 执行拷贝资源、修改本地文件的操作

    Args:
        release: release 为True 标识本地构建打包，commit的message为打包时间记录
        release 为False 标识构建离线基座，commit的message为离线基座打包时间记录

    Returns:
        int: 0 表示成功，1 表示失败
    """

    is_ready, manifest_info, resources_dir = check_uni_project()
    if not is_ready:
        # 校验资源目录失败，不能打包
        logging.error("本地资源文件校验失败")
        return 1
    # 更新UNI_APP_ID
    config.UNI_APP_ID = manifest_info["uniapp_id"]
    # 检查Git分支
    if not check_git_branch(config.ANDROID_UNI_BASE_PATH, os.getenv("TARGET_BRANCH")):
        logging.error("Git分支检查失败，终止执行")
        return 1

    # 检查APPS_DIRECTORY目录结构
    if not check_apps_directory():
        logging.error("APPS_DIRECTORY目录结构检查失败，终止执行")
        return 1

    # 清空目标目录
    if not clear_directory(config.APPS_DIRECTORY):
        logging.error("清空目标目录失败，终止执行")
        return 1

    # 提取文件
    if not extract_compressed_file("", config.APPS_DIRECTORY, resources_dir, False):
        logging.error("解压文件失败，终止执行")
        return 1
    # 更新build.gradle
    if not update_build_gradle(
            config.BUILD_GRADLE_PATH,
            (
                    f"{os.getenv("PROD_NAME")}_release_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    if release
                    else "android_debug"
            ),
            manifest_info,
    ):
        logging.error("更新build.gradle失败，终止执行")
        return 1

    # 更新 dcloud_control.xml 文件
    if not update_control_file(config.CONTROL_FILE_PATH, manifest_info["uniapp_id"], not release):
        logging.error("更新 dcloud_control.xml 文件失败，终止执行")
        return 1

    # 跟新 AndroidManifest.xml 文件，更新权限
    if not update_android_manifest(config.ANDROID_MANIFEST_PATH, manifest_info):
        logging.error("更新 AndroidManifest.xml 文件失败，终止执行")
        return 1

    logging.info("所有操作执行成功")
    return 0


def local_build(release):
    """
    本地构建：
    1. 从环境变量读取本地构建的目标输出目录
    2. 执行构建

    Args:
        release: 如果release 则输出产物到指定的位置，否则输出到当前UniApp项目的基座位置

    Returns:
        int: 0 表示成功，1 表示失败
    """
    from auto_assemble.build import main as build_main

    # 从环境变量读取本地构建的目标输出目录
    if release:
        target_dir = os.getenv("APK_OUTPUT_DIR")
    else:
        # 获取环境变量
        workspace = os.getenv("UNIAPP_WORKSPACE")
        is_cli = os.getenv("UNIAPP_IS_CLI", "n").lower() == "y"
        target_dir = os.path.join(workspace, "dist" if is_cli else "unpackage", "debug")
    return build_main(target_dir, release, is_distribution=False)


def local_assemble(release=True):
    """
    本地打包流程：
    1. 本地资源拷贝
    2. 本地构建
    Args:
        release: 如果release 则输出产物到指定的位置，否则输出到当前UniApp项目的基座位置

    Returns:

    """
    setup_logging(True, "本地打包流程" if release else "构建离线基座")
    if local_copy_res(release) != 0:
        logging.warning("本地资源拷贝中断，终止执行")
        return 1
    if local_build(release) != 0:
        logging.warning("本地打包中断，终止执行")
        return 1
    pass
