import logging
import os
import shutil
from datetime import datetime
from typing import Optional, Tuple

import patoolib

from auto_assemble.config import config
from auto_assemble.git import sync_repository, check_git_branch
from auto_assemble.log import setup_logging
from auto_assemble.parse_readme import parse_readme
from auto_assemble.update_android_manifest import update_android_manifest
from auto_assemble.update_build_gradle import update_build_gradle
from auto_assemble.update_control_file import update_control_file


def check_dependencies():
    """
    检查必要的依赖是否已安装
    Raises:
        ImportError: 当缺少必要的依赖时抛出
    """
    try:
        import rarfile
        import zipfile
    except ImportError as e:
        logging.error(f"缺少必要的依赖: {e}")
        raise


def check_paths():
    """
    检查必要的路径是否存在
    Raises:
        FileNotFoundError: 当必要的路径不存在时抛出
    """
    paths_to_check = {
        "仓库路径": config.DISTRIBUTION_PATH,
        "应用目录": config.APPS_DIRECTORY,
        "Gradle文件": config.BUILD_GRADLE_PATH,
    }

    for name, path in paths_to_check.items():
        if not os.path.exists(path):
            error_msg = f"{name}不存在: {path}"
            logging.error(error_msg)
            raise FileNotFoundError(error_msg)


def find_latest_directory(base_path: str) -> str:
    """
    查找最新的目录（基于时间戳命名）
    Args:
        base_path: 基础路径
    Returns:
        最新目录的完整路径
    Raises:
        ValueError: 当没有找到符合条件的目录时抛出
    """
    try:
        directories = [
            d for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d))
        ]
        if not directories:
            raise ValueError(f"在 {base_path} 中没有找到目录")

        latest_dir = max(directories, key=lambda d: datetime.strptime(d, "%Y%m%d%H%M"))
        latest_path = os.path.join(base_path, latest_dir)
        logging.info(f"找到最新目录: {latest_path}")
        return latest_path
    except ValueError as e:
        logging.error(f"查找最新目录失败: {e}")
        raise


def find_compressed_file(directory: str) -> Optional[str]:
    """
    在指定目录中查找压缩文件（.zip或.rar）
    Args:
        directory: 要搜索的目录
    Returns:
        压缩文件的完整路径，如果未找到则返回None
    """
    try:
        for file in os.listdir(directory):
            if file.endswith((".zip", ".rar")):
                file_path = os.path.join(directory, file)
                logging.info(f"找到压缩文件: {file_path}")
                return file_path
        logging.warning(f"在 {directory} 中未找到压缩文件")
        return None
    except Exception as e:
        logging.error(f"查找压缩文件时发生错误: {e}")
        return None


def clear_directory(directory: str) -> bool:
    """
    清空指定目录中的所有文件和子目录
    Args:
        directory: 要清空的目录
    Returns:
        bool: 清空是否成功
    """
    try:
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        logging.info(f"成功清空目录: {directory}")
        return True
    except Exception as e:
        logging.error(f"清空目录时发生错误: {e}")
        return False


def check_compressed_file_content(compressed_file: str) -> Tuple[bool, str]:
    """
    检查压缩文件中的目录结构是否符合要求
    Args:
        compressed_file: 压缩文件路径
    Returns:
        Tuple[bool, str]: (是否符合要求, 临时目录路径)
    """
    # 创建临时目录用于检查压缩文件内容
    temp_dir = os.path.join(os.path.dirname(compressed_file), "temp_check")
    try:
        logging.info(f"开始检查压缩文件内容: {compressed_file}")
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.makedirs(temp_dir)
        logging.info(f"创建临时目录: {temp_dir}")

        # 解压文件到临时目录
        logging.info("开始解压文件到临时目录")
        patoolib.extract_archive(compressed_file, outdir=temp_dir)

        # 检查目录结构
        contents = os.listdir(temp_dir)
        logging.info(f"压缩文件内容: {contents}")
        if len(contents) != 1:
            logging.error(f"压缩文件中包含多个目录或文件: {contents}")
            # 检查失败，清理临时目录
            shutil.rmtree(temp_dir)
            return False, ""
        if contents[0] != config.UNI_APP_ID:
            logging.error(
                f"压缩文件中的目录名称与UNI_APP_ID不匹配: {contents[0]} != {config.UNI_APP_ID}"
            )
            # 检查失败，清理临时目录
            shutil.rmtree(temp_dir)
            return False, ""

        logging.info("压缩文件内容检查通过")
        # 检查通过，保留临时目录
        return True, temp_dir
    except Exception as e:
        logging.error(f"检查压缩文件内容时发生错误: {e}")
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        return False, ""


def extract_compressed_file(
        compressed_file: str, extract_to: str, temp_dir: str, rm_temp: bool = True
) -> bool:
    """
    解压文件到指定目录，如果临时解压目录已存在，则直接复制文件
    Args:
        compressed_file: 压缩文件路径
        extract_to: 解压目标目录
        temp_dir: 已存在的资源目录缓存
        rm_temp: 提取后是否移除原资源文件
    Returns:
        bool: 解压是否成功
    """
    try:
        if os.path.exists(temp_dir) and os.listdir(temp_dir):
            logging.info(f"发现临时解压目录，直接复制文件: {temp_dir} -> {extract_to}")
            # 获取临时目录中的应用目录
            app_dir = os.path.join(temp_dir, config.UNI_APP_ID)
            if os.path.exists(app_dir):
                # 复制应用目录到目标目录
                target_dir = os.path.join(extract_to, config.UNI_APP_ID)
                if not os.path.exists(target_dir):
                    os.makedirs(target_dir)
                # 复制文件
                for item in os.listdir(app_dir):
                    s = os.path.join(app_dir, item)
                    d = os.path.join(target_dir, item)
                    if os.path.isdir(s):
                        shutil.copytree(s, d, dirs_exist_ok=True)
                    else:
                        shutil.copy2(s, d)
                logging.info(f"成功从临时目录复制文件到: {extract_to}")
                if rm_temp:
                    # 清理临时目录
                    shutil.rmtree(temp_dir)
                return True
            else:
                logging.error(f"临时目录中未找到应用目录: {app_dir}")
                return False
        else:
            # 临时目录不存在，执行正常解压
            logging.info(f"临时解压目录不存在，执行正常解压: {compressed_file} -> {extract_to}")
            patoolib.extract_archive(compressed_file, outdir=extract_to)
            logging.info(f"成功解压文件到: {extract_to}")
            return True
    except Exception as e:
        logging.error(f"解压文件时发生错误: {e}")
        return False


def check_apps_directory() -> bool:
    """
    检查APPS_DIRECTORY目录下的目录结构是否符合要求
    Returns:
        bool: 是否符合要求
    """
    try:
        logging.info(f"开始检查APPS_DIRECTORY目录结构: {config.APPS_DIRECTORY}")
        contents = os.listdir(config.APPS_DIRECTORY)
        logging.info(f"目录内容: {contents}")
        # 检查目录数量是否为1，不为1则警告
        if len(contents) > 1:
            logging.warning(f"APPS_DIRECTORY中包含多个目录或文件: {contents}")

        # 检查目录名称是否与UNI_APP_ID一致,不一致则警告
        if len(contents) == 1 and contents[0] != config.UNI_APP_ID:
            logging.warning(
                f"APPS_DIRECTORY中的目录名称与UNI_APP_ID不匹配: {contents[0]} != {config.UNI_APP_ID}"
            )

        logging.info("APPS_DIRECTORY目录结构检查通过")
        return True
    except Exception as e:
        logging.error(f"检查APPS_DIRECTORY时发生错误: {e}")
        return False


def get_project_name(distribution_path: str) -> Tuple[str, str]:
    """
    从分发仓库中获取最新的项目名称和最新时间戳目录
    Args:
        distribution_path: 分发仓库路径
    Returns:
        Tuple[str, str]: (项目名称, 最新时间戳目录的完整路径)
    Raises:
        ValueError: 当无法获取项目名称时抛出
    """
    try:
        # 获取分发仓库下的所有目录（项目目录）
        project_dirs = [
            d
            for d in os.listdir(distribution_path)
            if os.path.isdir(os.path.join(distribution_path, d))
        ]
        if not project_dirs:
            raise ValueError(f"在 {distribution_path} 中没有找到项目目录")

        # 遍历所有项目目录，找到最新的时间戳目录
        latest_project = None
        latest_timestamp = None
        latest_timestamp_path = None

        for project_dir in project_dirs:
            project_path = os.path.join(distribution_path, project_dir)
            # 获取项目目录下的所有时间戳目录
            timestamp_dirs = [
                d for d in os.listdir(project_path) if os.path.isdir(os.path.join(project_path, d))
            ]
            if not timestamp_dirs:
                continue

            # 获取最新的时间戳目录
            try:
                latest_timestamp_dir = max(
                    timestamp_dirs, key=lambda d: datetime.strptime(d, "%Y%m%d%H%M")
                )
                if latest_timestamp is None or latest_timestamp_dir > latest_timestamp:
                    latest_timestamp = latest_timestamp_dir
                    latest_project = project_dir
                    latest_timestamp_path = os.path.join(project_path, latest_timestamp_dir)
            except ValueError:
                continue

        if latest_project is None:
            raise ValueError(f"在 {distribution_path} 中没有找到有效的时间戳目录")

        logging.info(f"获取到项目名称: {latest_project}, 最新时间戳目录: {latest_timestamp_path}")
        return latest_project, latest_timestamp_path
    except Exception as e:
        logging.error(f"获取项目名称失败: {e}")
        raise


def main():
    """
    主函数：执行整个更新流程
    1. 配置日志系统
    2. 检查依赖和路径
    3. 同步Git仓库
    4. 获取项目名称和最新目录
    5. 检查是否已存在对应的APK文件，如果不存在则读取README.md获取版本信息
    6. 查找压缩文件
    7. 检查压缩文件内容（确保只有一个目录且目录名与UNI_APP_ID一致）
    8. 检查Git分支（确保在PROJECT_BRANCH分支）
    9. 检查APPS_DIRECTORY目录结构（确保只有一个目录且目录名与UNI_APP_ID一致）
    10. 清空目标目录
    11. 解压文件
    12. 更新build.gradle
    13. 更新control文件
    14. 更新 AndroidManifest.xml 文件，更新权限
    """
    try:
        # 配置日志
        setup_logging(clear_log_file=True, task_name="执行更新流程")

        # 检查依赖和路径
        check_dependencies()
        check_paths()

        # 同步仓库
        if not sync_repository(config.DISTRIBUTION_PATH):
            logging.error("Git仓库同步失败，终止执行")
            return

        # 获取项目名称和最新目录
        try:
            config.PROD_NAME, latest_dir = get_project_name(config.DISTRIBUTION_PATH)
            logging.info(f"获取到项目名称: {config.PROD_NAME}")
        except ValueError as e:
            logging.error(f"获取项目名称失败: {e}")
            return 1

        # 查找是否已存在对应的APK文件
        latest_dir_name = os.path.basename(latest_dir)
        apk_file = os.path.join(latest_dir, f"{latest_dir_name}.apk")

        # 如果存在产物，则无需执行打包
        if os.path.exists(apk_file):
            logging.info(f"已经存在产物 {apk_file} 无需执行打包")
            return 1

        logging.info(f"不存在产物 {apk_file} 需要执行打包")
        readme_path = os.path.join(latest_dir, "README.md")
        readme_info = parse_readme(readme_path)

        # 更新UNI_APP_ID
        config.UNI_APP_ID = readme_info["uniapp_id"]
        # 查找压缩文件
        compressed_file = find_compressed_file(latest_dir)
        if not compressed_file:
            logging.error("未找到压缩文件，终止执行")
            return 1

        # 检查压缩文件内容
        check_result, temp_dir = check_compressed_file_content(compressed_file)
        if not check_result:
            logging.error("压缩文件内容检查失败，终止执行")
            return 1

        # 检查Git分支
        if not check_git_branch(config.ANDROID_UNI_BASE_PATH):
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

        # 解压文件
        if not extract_compressed_file(compressed_file, config.APPS_DIRECTORY, temp_dir):
            logging.error("解压文件失败，终止执行")
            return 1

        # 更新build.gradle
        if not update_build_gradle(
                config.BUILD_GRADLE_PATH,
                os.path.basename(latest_dir),
                readme_info,
        ):
            logging.error("更新build.gradle失败，终止执行")
            return 1

        # 更新 dcloud_control.xml 文件
        if not update_control_file(config.CONTROL_FILE_PATH, readme_info["uniapp_id"]):
            logging.error("更新 dcloud_control.xml 文件失败，终止执行")
            return 1

        # 跟新 AndroidManifest.xml 文件，更新权限
        if not update_android_manifest(config.ANDROID_MANIFEST_PATH, readme_info):
            logging.error("更新 AndroidManifest.xml 文件失败，终止执行")
            return 1

        logging.info("所有操作执行成功")
        return 0
    except Exception as e:
        logging.error(f"执行过程中发生错误: {e}")
        return 1


if __name__ == "__main__":
    main()
