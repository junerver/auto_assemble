import logging
import os
import shutil
import subprocess
import sys
import textwrap
import zipfile
from pathlib import Path
from typing import Optional


from common.commit_label import parse_build_req_message, parse_build_branch
from auto_assemble.immediate_push import migrate_test_to_release, migrate_same_build_mode
from common.api import fetch_task_info, record_task_res_fp, fetch_task_info_by_res_fp
from common.error import BusinessException
from common.extract import modern_extract
from common.gitlab import compare_readme_file
from common.log import setup_logging
from auto_assemble.parse_readme import parse_readme
from auto_assemble.update_android_manifest import update_android_manifest
from auto_assemble.update_build_gradle import update_build_gradle
from auto_assemble.update_control_file import update_control_file
from common.client_publish import client_publish_async
from common.config import config
from common.git import sync_repository, check_git_branch, git_reset_and_clean
from common.md5 import calculate_zip_fingerprint
from common.task_util import local_task_dir
from common.types import ManifestInfo, TaskInfo


def check_paths():
    """
    检查必要的路径是否存在
    Raises:
        FileNotFoundError: 当必要的路径不存在时抛出
    """
    paths_to_check = {
        "分发仓库仓库目录": Path(config.DISTRIBUTION_PATH),
        "UniApp应用目录apps目录": Path(config.APPS_DIRECTORY),
        "基座项目Gradle文件": Path(config.BUILD_GRADLE_PATH),
    }

    for name, path in paths_to_check.items():
        if not path.exists():
            error_msg = f"{name}不存在: {path}"
            logging.error(error_msg)
            raise FileNotFoundError(error_msg)


def find_compressed_file(directory: Path) -> Optional[Path]:
    """
    在指定目录中查找压缩文件（.zip或.rar）
    Args:
        directory: 要搜索的目录
    Returns:
        压缩文件的完整路径，如果未找到则返回None
    """
    try:
        for file in directory.iterdir():
            if file.name.endswith((".zip", ".rar")):
                logging.info(f"找到压缩文件: {file}")
                return file
        logging.warning(f"在 {directory} 中未找到压缩文件")
        return None
    except Exception as e:
        logging.exception(f"查找压缩文件时发生错误: {e}")
        return None


def clear_directory(directory: Path) -> bool:
    """
    清空指定目录中的所有文件和子目录
    Args:
        directory: 要清空的目录
    Returns:
        bool: 清空是否成功
    """
    try:
        for file_path in directory.iterdir():
            if file_path.is_file():
                os.unlink(file_path)
            elif file_path.is_dir():
                shutil.rmtree(file_path)
        logging.info(f"成功清空目录: {directory}")
        return True
    except Exception as e:
        logging.exception(f"清空目录时发生错误: {e}")
        return False


def check_compressed_file_content(compressed_file: Path) -> tuple[bool, Optional[Path]]:
    """
    检查压缩文件中的目录结构是否符合要求
    Args:
        compressed_file: 压缩文件路径
    Returns:
        Tuple[bool, str]: (是否符合要求, 临时目录路径)
    """
    # 创建临时目录用于检查压缩文件内容
    temp_dir = compressed_file.resolve().parent / "temp_check"
    try:
        logging.info(f"开始检查压缩文件内容: {compressed_file}")
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        temp_dir.mkdir(parents=True, exist_ok=True)
        logging.info(f"创建临时目录: {temp_dir}")

        # 解压文件到临时目录
        logging.info("开始解压文件到临时目录")
        modern_extract(compressed_file, outdir=temp_dir)

        # 检查目录结构
        contents = list(temp_dir.iterdir())
        logging.info(f"压缩文件内容: {contents}")
        if len(contents) != 1:
            logging.error(f"压缩文件中包含多个目录或文件: {contents}")
            # 检查失败，清理临时目录
            shutil.rmtree(temp_dir)
            return False, None
        if contents[0].name != config.UNI_APP_ID:
            logging.error(f"压缩文件中的目录名称与UNI_APP_ID不匹配: {contents[0]} != {config.UNI_APP_ID}")
            # 检查失败，清理临时目录
            shutil.rmtree(temp_dir)
            return False, None

        logging.info("压缩文件内容检查通过")
        # 检查通过，保留临时目录
        return True, temp_dir
    except Exception as e:
        logging.exception(f"检查压缩文件内容时发生错误: {e}")
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        return False, None


def extract_compressed_file(
    compressed_file: Path,
    extract_to: Path,
    temp_dir: Path,
    rm_temp: bool = True,
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
        if temp_dir.is_dir() and list(temp_dir.iterdir()):
            logging.info(f"发现临时解压目录，直接复制文件: {temp_dir} -> {extract_to}")
            # 获取临时目录中的应用目录
            temp_app_dir = temp_dir / config.UNI_APP_ID
            if temp_app_dir.exists():
                # 复制应用目录到目标目录
                target_dir = extract_to / config.UNI_APP_ID
                if not target_dir.exists():
                    target_dir.mkdir(parents=True, exist_ok=True)
                # 复制文件
                for item in temp_app_dir.iterdir():
                    s = item
                    d = target_dir / item.name
                    if s.is_dir():
                        shutil.copytree(s, d, dirs_exist_ok=True)
                    else:
                        shutil.copy2(s, d)
                logging.info(f"成功从临时目录复制文件到: {extract_to}")
                if rm_temp:
                    # 清理临时目录
                    shutil.rmtree(temp_dir)
                return True
            else:
                logging.error(f"临时目录中未找到应用目录: {temp_app_dir}")
                return False
        else:
            # 临时目录不存在，执行正常解压
            logging.info(f"临时解压目录不存在，执行正常解压: {compressed_file} -> {extract_to}")
            modern_extract(compressed_file, outdir=extract_to)
            logging.info(f"成功解压文件到: {extract_to}")
            return True
    except Exception as e:
        logging.exception(f"解压文件时发生错误: {e}")
        return False


def check_apps_directory() -> bool:
    """
    检查APPS_DIRECTORY目录下的目录结构是否符合要求
    Returns:
        bool: 是否符合要求
    """
    try:
        logging.info(f"开始检查APPS_DIRECTORY目录结构: {config.APPS_DIRECTORY}")
        contents = list(Path(config.APPS_DIRECTORY).iterdir())
        logging.info(f"目录内容: {contents}")
        # 检查目录数量是否为1，不为1则警告
        if len(contents) > 1:
            logging.warning(f"APPS_DIRECTORY中包含多个目录或文件: {contents}")

        # 检查目录名称是否与UNI_APP_ID一致,不一致则警告
        if len(contents) == 1 and contents[0].name != config.UNI_APP_ID:
            logging.warning(f"APPS_DIRECTORY中的目录名称与UNI_APP_ID不匹配: {contents[0].name} != {config.UNI_APP_ID}")

        logging.info("APPS_DIRECTORY目录结构检查通过")
        return True
    except Exception as e:
        logging.exception(f"检查APPS_DIRECTORY时发生错误: {e}")
        return False


def copy_res(prod_name: str, task_dir: str) -> int:
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

    Args:
        prod_name: 项目名称，用于指向本次需要构建的项目，对应本地基座的 f"prod_{prod_name}" 分支
        task_dir: 任务目录的名称，用于指向本次构建任务的目录，如果为空，则从分发仓库中获取最新的项目名称和最新时间戳目录
    Returns:
        int: 返回0表示成功，返回1表示失败
    """
    # uni资源包的临时解压目录
    temp_dir: Optional[Path] = None  # 初始化为None
    # 用于混淆资源包的工作目录
    obfuscated_dir: Optional[Path] = None  # Initialize obfuscated_dir to None
    try:
        # 配置日志
        setup_logging(clear_log_file=True, task_name="执行资源同步流程")

        # 检查路径
        check_paths()

        # 获取项目名称和最新目录
        try:
            logging.info(f"本次构建任务ID: {config.cur_task_id}")

            # 请求webhook服务的/task/<task_id>接口，获取提交信息
            def on_success(task_info: TaskInfo):
                config.build_mode, commit_message = parse_build_req_message(task_info.commit_message)
                config.last_commit_message = textwrap.dedent(
                    f"""

                    提交时间：{task_info.created_at}
                    提交人: {task_info.author}
                    提交信息: {commit_message}
                    提交哈希: {task_info.commit_hash}
                    """
                )
                if not config.BASE_ON_GITLAB:
                    config.cur_task_dir = local_task_dir(config.cur_task_id, config.build_mode)

            # 请求构建任务相关信息
            fetch_task_info(config.cur_task_id, on_success, lambda e: None)
        except ValueError as e:
            logging.error(f"获取项目名称失败: {e}")
            return 10001

        if config.build_mode not in ["dev", "test", "release"]:
            logging.error(f"构建模式错误: {config.build_mode}")
            return 11015
        if config.BASE_ON_GITLAB:
            # 检查目标分支
            check_git_branch(
                config.DISTRIBUTION_PATH,
                parse_build_branch(config.build_mode),
            )

            # 同步仓库
            if not sync_repository(config.DISTRIBUTION_PATH, branch=parse_build_branch(config.build_mode)):
                logging.error("Git仓库同步失败，终止执行")
                return 11002

        # 查找是否已存在对应的APK文件
        latest_dir_name: str = config.cur_task_dir.name
        apk_file: Path = config.cur_task_dir / f"{latest_dir_name}.apk"

        # 如果存在产物，则无需执行打包
        if apk_file.exists():
            logging.info(f"已经存在产物 {apk_file} 无需执行打包")
            return 11003

        logging.info(f"不存在产物 {apk_file} 需要执行打包")
        readme_path: Path = config.cur_task_dir / "README.md"
        # 解析readme文件拿到本次打包请求所需的内容
        client_publish_async("build", "构建任务:copy_res", "开始解析请求文件 README.md ...")
        readme_info: Optional[ManifestInfo] = parse_readme(readme_path)
        if readme_info is None:
            logging.error("解析readme文件失败，终止执行")
            return 11016

        # 更新UNI_APP_ID
        config.UNI_APP_ID = readme_info["uniapp_id"]
        # 查找压缩文件
        compressed_file = find_compressed_file(config.cur_task_dir)
        if not compressed_file:
            logging.error("未找到压缩文件，终止执行")
            return 11004

        # 计算本次资源包指纹，存储在数据库中
        fingerprint = calculate_zip_fingerprint(compressed_file)
        logging.info(f"本次资源包指纹: {fingerprint}")
        record_task_res_fp(
            config.cur_task_id,
            fingerprint,
            lambda msg: logging.info(msg),
            lambda err: logging.error(err),
        )

        # 本次构建是release，查找是否存在相同指纹的构建任务，对比其readme文件、构建是否成功
        old_task = fetch_task_info_by_res_fp(fingerprint)
        if old_task and old_task.status == "completed" and compare_readme_file(old_task, readme_path):
            new_mode: str = config.build_mode
            old_mode: str = parse_build_req_message(old_task.commit_title)[0]
            # 径直推送支持下面的几种模式
            try:
                match (old_mode, new_mode):
                    case ("test", "release"):
                        logging.info("旧构建是test，需要执行归一化、重签名")
                        migrate_test_to_release(old_task)
                    case _ if old_mode == new_mode:
                        # 所有模式相同的情况统一处理
                        logging.debug(f"新旧模式相同({new_mode})，无需特殊处理")
                        migrate_same_build_mode(old_task)
                    case _:
                        logging.info(f"无法迁移的模式:{new_mode}->{new_mode}")
            except Exception as e:
                if isinstance(e, BusinessException) and e.code == 0:
                    logging.info("触发径直推送，直接执行归一化成功，结束任务执行！")
                    raise e
                logging.error("径直推送失败，回退到常规操作")
        else:
            logging.info("该资源包构建结果不存在，执行常规流程")

        # 检查压缩文件内容
        check_result, temp_dir = check_compressed_file_content(compressed_file)
        if not check_result:
            logging.error("压缩文件内容检查失败，终止执行")
            raise BusinessException(11005)

        # 检查Git分支
        if not check_git_branch(config.ANDROID_UNI_BASE_PATH, config.PROD_BRANCH):
            logging.error("Git分支检查失败，终止执行")
            raise BusinessException(12001)

        # 检查APPS_DIRECTORY目录结构
        if not check_apps_directory():
            logging.error("APPS_DIRECTORY目录结构检查失败，终止执行")
            raise BusinessException(12002)

        # 清空目标目录
        if not clear_directory(Path(config.APPS_DIRECTORY)):
            logging.error("清空目标目录失败，终止执行")
            raise BusinessException(12003)

        if config.build_mode != "dev":
            # obfuscated_dir: Optional[Path] = None # Remove this line
            try:
                client_publish_async("build", "构建任务:copy_res", "开始执行资源混淆...")
                # release 构建模式下需要对代码进行混淆，执行javascript-obfuscator命令混淆temp_dir目录下的所有js文件
                # 在当前目录下复制temp_dir目录，作为混淆后的目录
                obfuscated_dir = config.cur_task_dir / "obfuscated"
                if not obfuscated_dir.exists():
                    shutil.copytree(temp_dir, obfuscated_dir)
                logging.info(f"复制temp_dir目录到混淆后的目录: {obfuscated_dir}")
                if sys.platform == "win32":
                    obfuscator_cmd = "javascript-obfuscator.cmd"
                else:
                    obfuscator_cmd = "javascript-obfuscator"

                # 获取混淆等级
                preset_map = {
                    "default": "default",
                    "low": "low-obfuscation",
                    "medium": "medium-obfuscation",
                    "high": "high-obfuscation",
                }
                preset = os.getenv("OBFUSCATOR_PRESET", "low")
                cmd = [
                    obfuscator_cmd,
                    str(obfuscated_dir),
                    "--output",
                    str(obfuscated_dir),
                    "--options-preset",
                    preset_map[preset],
                ]
                logging.info(f"执行javascript-obfuscator命令: {cmd}")
                result = subprocess.run(cmd, check=True)
                if result.returncode == 0:
                    logging.info(f"javascript-obfuscator命令执行成功，混淆后的目录: {obfuscated_dir}")
                    # 将混淆后的目录压缩为zip文件，作为留痕
                    zip_file_path: Path = config.cur_task_dir / f"{latest_dir_name}_obfuscated.bak"
                    with zipfile.ZipFile(zip_file_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                        for file_path in obfuscated_dir.rglob("*"):
                            if file_path.is_file():
                                arcname = Path(config.UNI_APP_ID) / file_path.relative_to(obfuscated_dir)
                                zipf.write(file_path, arcname)
                    logging.info(f"混淆后的目录压缩为bak文件进行备份: {zip_file_path}")
                    # 删除原目录
                    shutil.rmtree(temp_dir)
                    # 将混淆后的目录作为临时目录
                    temp_dir = obfuscated_dir
                    config.is_obfuscated = True
                    client_publish_async("build", "构建任务:copy_res", "混淆完成")
                else:
                    config.is_obfuscated = False
                    logging.error(f"javascript-obfuscator命令执行失败: {result.returncode}，回退使用原始代码")
                    # 执行失败，不进行混淆
                    if obfuscated_dir is not None and obfuscated_dir.exists():
                        shutil.rmtree(obfuscated_dir)
                    client_publish_async("build", "构建任务:copy_res", "混淆失败，回退使用原始代码")
            except Exception as e:
                logging.exception(f"执行javascript-obfuscator命令失败: {e}")
                # 执行失败，不进行混淆
                if obfuscated_dir is not None and obfuscated_dir.exists():  # Add is not None check
                    shutil.rmtree(obfuscated_dir)
        else:
            # 无需混淆
            logging.info("无需混淆，直接解压文件")

        # 解压文件
        if not extract_compressed_file(compressed_file, Path(config.APPS_DIRECTORY), temp_dir):
            logging.error("解压文件失败，终止执行")
            raise BusinessException(12004)

        # 更新build.gradle
        client_publish_async("build", "构建任务:copy_res", "开始执行更新基座工程构建脚本...")
        try:
            if not update_build_gradle(
                Path(config.BUILD_GRADLE_PATH),
                latest_dir_name,
                readme_info,
            ):
                logging.error("更新build.gradle失败，终止执行")
                raise BusinessException(12005)
        except KeyError as e:
            logging.error(f"更新build.gradle失败: {e}")
            raise BusinessException(12009)

        # 更新 dcloud_control.xml 文件
        if not update_control_file(
            Path(config.CONTROL_FILE_PATH),
            readme_info["uniapp_id"],
            config.build_mode == "dev",
        ):
            logging.error("更新 dcloud_control.xml 文件失败，终止执行")
            raise BusinessException(12006)

        # 跟新 AndroidManifest.xml 文件，更新权限
        if not update_android_manifest(Path(config.ANDROID_MANIFEST_PATH), readme_info):
            logging.error("更新 AndroidManifest.xml 文件失败，终止执行")
            raise BusinessException(12007)

        logging.info("所有操作执行成功")
        client_publish_async("build", "构建任务:copy_res", "基座工程更新完成...")
        return 0
    except Exception as e:
        # 清理
        git_reset_and_clean(repo_path=config.DISTRIBUTION_PATH)
        if isinstance(e, FileNotFoundError):
            logging.error(f"目录不存在: {e}")
            return 10004
        elif isinstance(e, ImportError):
            logging.error(f"配置文件错误: {e}")
            return 10005
        elif isinstance(e, BusinessException):
            if e.code == 0:
                raise e
            logging.error(f"业务错误: {e.code} {e.message}")
            return e.code
        else:
            logging.exception(f"执行过程中发生错误: {e}")
        return 1
    finally:
        if temp_dir is not None and temp_dir.exists():
            shutil.rmtree(temp_dir)
