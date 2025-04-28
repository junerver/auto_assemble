import json
import logging
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime

from auto_assemble.check_uni_base import check_uni_base
from auto_assemble.config import config
from auto_assemble.git import git_push, git_reset_and_clean
from auto_assemble.log import setup_logging
from auto_assemble.push import git_add, git_commit, get_staged_files


def get_build_req_label(build_mode: str, req_resp: str = "req"):
    """
    获取构建请求标签
    Args:
        req_resp: 请求标识、响应标识
        build_mode (str): 构建模式，可选值：dev、test、release
    Returns:
        str: 构建请求标签
    """
    return f"#{build_mode}_{req_resp}# "


def get_build_resp_message(commit_message: str):
    return f"{get_build_req_label(config.build_mode, 'resp')}{commit_message}"


def parse_build_req_message(message: str):
    """
    解析构建请求标签
    Args:
        message (str): 构建请求消息，它是一个 `#{build_mode}_req# {commit_message}` 格式的字符串，需要通过正则提取出build_mode和commit_message
    Returns:
        tuple: 构建模式，构建请求类型
    """
    pattern = r"#(\w+)_req#\s*(.*)"
    match = re.search(pattern, message)
    if match:
        return match.group(1), match.group(2)
    return None, None


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


def get_distribution_target_dir(apk_name: str):
    """
    根据APK文件名生成目标目录
    Args:
        apk_name (str): APK文件名
    Returns:
        str: 目标目录路径
    """
    return os.path.join(config.DISTRIBUTION_PATH, config.PROD_NAME, apk_name.replace(".apk", ""))


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
        if sys.platform == "win32":
            cmd = [
                "cmd",
                "/c",
                "gradlew.bat",
                "clean",
                f"app:assemble{'Release' if release else 'Debug'}",
            ]
        else:
            cmd = [
                "./gradlew",
                "clean",
                f"app:assemble{'Release' if release else 'Debug'}",
            ]
        logging.info(f"执行命令: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",  # ✅ 修改为 utf-8
            errors="replace",  # ✅ 可选，避免报错，替换非法字符
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


def copy_build_outputs(apk_name: str, target_dir: str, release: bool) -> tuple[bool, str]:
    """
    复制构建产物到目标目录，将从分发仓库获取的提交信息补充到元数据文件中，并创建md5作为文件名的空白文件

    Args:
        apk_name: APK文件名
        target_dir: 目标目录
        release: 是否为release包
    Returns:
        tuple<bool, str>: 复制是否成功, apk文件名(不包含尾缀)
    """
    try:
        # 确保目标目录存在
        os.makedirs(target_dir, exist_ok=True)
        # 根据构建模式确定输出目录
        output_dir = config.BUILD_RELEASE_OUTPUT_DIR if release else config.BUILD_DEBUG_OUTPUT_DIR
        # 复制APK文件
        source_apk = os.path.join(output_dir, apk_name)
        target_apk = os.path.join(target_dir, apk_name)

        if os.path.exists(source_apk):
            shutil.copy2(source_apk, target_apk)
            logging.info(f"成功复制APK文件: {apk_name}")
        else:
            logging.error(f"源APK文件不存在: {source_apk}")
            return False, ""

        # 复制metadata文件
        source_metadata = os.path.join(output_dir, "release-metadata.md")
        target_metadata = os.path.join(target_dir, "release-metadata.md")

        if os.path.exists(source_metadata):
            # 提取metadata文件中的MD5字段
            with open(source_metadata, "r", encoding="utf-8") as f:
                content = f.read()
                md5 = re.search(r"MD5: (\w+)", content).group(1)
            # 复制metadata文件
            shutil.copy2(source_metadata, target_metadata)
            # 在metadata末尾追加写入
            with open(target_metadata, "a", encoding="utf-8") as f:
                f.write(
                    f"\n\n打包请求: {config.last_commit_message}\n\nUniApp资源包是否混淆: {config.is_obfuscated}"
                )
            # 在目标目录下创建md5作为文件名的空白文件
            open(os.path.join(target_dir, md5), "w").close()
            logging.info("成功复制metadata文件")

            # todo: 解析metadata文件，调用接口，记录任务对应的元数据
            # 解析metadata文件
            with open(target_metadata, "r", encoding="utf-8") as f:
                metadata_text = f.read()
            # 解析metadata文件
            metadata = parse_metadata(metadata_text)
            logging.info(f"解析metadata文件结果: {json.dumps(metadata)}")

        else:
            logging.error(f"源metadata文件不存在: {source_metadata}")
            return False, ""

        return True, apk_name.replace(".apk", "")
    except Exception as e:
        logging.error(f"复制构建产物时发生错误: {e}")
        return False, ""


def parse_metadata(metadata_text: str):
    """
    解析metadata文件
    """
    # 原始 key 到 Python 风格 key 的映射表
    key_mapping = {
        "Package Name": "package_name",
        "Version Name": "version_name",
        "Version Code": "version_code",
        "Build Type": "build_type",
        "Flavor": "flavor",
        "Build Date": "build_date",
        "File Size": "file_size",
        "MD5": "md5",
        # "打包请求" intentionally omitted
    }

    # 转换为 dict 并跳过不需要的字段
    metadata = {}
    for line in metadata_text.strip().splitlines():
        if not line.strip():
            continue
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            if key in key_mapping:
                mapped_key = key_mapping[key]
                if mapped_key == "file_size":
                    # 提取开头的纯数字部分（字节数）
                    match = re.search(r"^\d+", value)
                    metadata[mapped_key] = int(match.group()) if match else 0
                else:
                    metadata[mapped_key] = value

    return metadata


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
            return 12008

        # 获取已暂存的文件
        staged_files = get_staged_files(repo_path=config.ANDROID_UNI_BASE_PATH)
        if not staged_files:
            logging.error("没有待提交的文件，资源文件未更新，终止执行")
            return 12011
        logging.info("待提交的文件列表:")
        for file in staged_files:
            logging.info(f"  - {file}")

        # 执行git commit
        if not git_commit(commit_message, repo_path=config.ANDROID_UNI_BASE_PATH):
            logging.error("git commit 执行失败")
            return 12012

        # 执行git push
        if not git_push(repo_path=config.ANDROID_UNI_BASE_PATH):
            logging.error("git push 执行失败")
            return 12013
        return 0
    except Exception as e:
        logging.error(f"更新git信息时发生错误: {e}")
        return 12014


def main(target_dir: str = None, release: bool = True, is_distribution: bool = True):
    """
    主函数：执行整个构建流程
    1. 配置日志系统
    2. 检查路径
    3. 执行gradle构建
    4. 复制构建产物

    Args:
        target_dir: 构建产物目标输出目录，可空，不传递时默认输出到分发目录下
        release: 指定构建类型，True 将构建release包，False 将构建debug包
        is_distribution: 是否分发，决定基座仓库的commit message格式
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
            return 20001

        # 获取从release目录读取构建产物名称
        apk_name = get_build_output_name(release)
        # 没有传递时，指向分发目录
        if not target_dir:
            target_dir = get_distribution_target_dir(apk_name)

        # 复制构建产物，返回是否成功和apk文件名
        success, apk_name = copy_build_outputs(apk_name, target_dir, release)
        if not success:
            logging.error("复制构建产物失败，终止执行")
            return 20002

        # 更新git信息，执行git add和git commit
        if is_distribution:
            # 来自分发的打包请求，附带提交打包请求的commit信息
            commit_message = f"release_req: {apk_name}{config.last_commit_message}"
        else:
            # 本地构建只记录变更时间
            commit_message = (
                f"{'release' if release else 'debug'}: {datetime.now().strftime('%Y%m%d%H%M%S')}"
            )

        if (git_code := update_git_info(commit_message)) != 0:
            logging.error("更新git信息失败，终止执行")
            return git_code

        logging.info("所有操作执行成功")
        return 0
    except Exception as e:
        logging.error(f"执行过程中发生错误: {e}")
        if isinstance(e, FileNotFoundError):
            return 12010
        return 1
    finally:
        # 清理
        logging.info("开始清理基座项目git缓存")
        git_reset_and_clean(repo_path=config.ANDROID_UNI_BASE_PATH)


if __name__ == "__main__":
    main()
