import json
import logging
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

from auto_assemble.check_uni_base import check_uni_base
from common.commit_label import get_build_req_label
from common.log import setup_logging
from auto_assemble.push import git_add, git_commit, get_staged_files
from auto_assemble.types import BuildMetadata, SignConfig
from common.client_publish import client_publish_async
from common.config import config
from common.git import git_push, git_reset_and_clean
from common.md5 import calculate_file_md5


def get_build_resp_message(commit_message: str):
    return f"{get_build_req_label(config.build_mode, 'resp')}{commit_message}"


def parse_build_req_message(message: str) -> tuple[Optional[str], Optional[str]]:
    """
    解析构建请求标签
    Args:
        message (str): 构建请求消息，它是一个 `#{build_mode}_req# {commit_message}` 格式的字符串，需要通过正则提取出build_mode和commit_message
    Returns:
        tuple: 构建模式，构建请求的commit message
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
    for file in os.listdir(config.BUILD_RELEASE_OUTPUT_DIR if release else config.BUILD_DEBUG_OUTPUT_DIR):
        if file.endswith(".apk"):
            return file
    raise FileNotFoundError("未找到符合yyyyMMddHHmm格式的APK文件")


def get_distribution_target_dir(apk_name: str) -> Path:
    """
    根据APK文件名生成目标目录
    Args:
        apk_name (str): APK文件名
    Returns:
        str: 目标目录路径
    """
    return Path(config.DISTRIBUTION_PATH) / config.PROD_NAME / apk_name.replace(".apk", "")


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
        if not Path(config.ANDROID_UNI_BASE_PATH).exists():
            logging.error(f"项目目录不存在: {config.ANDROID_UNI_BASE_PATH}")
            return False

        # 切换到项目目录
        os.chdir(config.ANDROID_UNI_BASE_PATH)
        logging.info(f"已切换到项目目录: {os.getcwd()}")

        # 检查 gradlew.bat 是否存在
        if not Path("gradlew.bat").exists():
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
            stdout=sys.stdout,
            stderr=sys.stderr,
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


# noinspection PyUnusedLocal,PyUnboundLocalVariable
def copy_build_outputs(apk_name: str, target_dir: Path, release: bool, sign_config: SignConfig) -> tuple[bool, str]:
    """
    复制构建产物到目标目录，将从分发仓库获取的提交信息补充到元数据文件中，并创建md5作为文件名的空白文件

    Args:
        apk_name: APK文件名
        target_dir: 目标目录
        release: 是否为release包
        sign_config: 项目签名配置信息
    Returns:
        tuple<bool, str>: 复制是否成功, apk文件名(不包含尾缀)
    """
    try:
        # 确保目标目录存在
        target_dir.mkdir(parents=True, exist_ok=True)
        # 根据构建模式确定输出目录
        output_dir: Path = Path(config.BUILD_RELEASE_OUTPUT_DIR if release else config.BUILD_DEBUG_OUTPUT_DIR)
        # 复制APK文件
        source_apk = output_dir / apk_name
        normalized_apk = output_dir / apk_name.replace(".apk", "_normalized.apk")
        target_apk = target_dir / apk_name
        is_normalized = False

        if source_apk.exists():
            if config.build_mode == "release":
                try:
                    client_publish_async("build", "构建任务:build", "开始执行ApkNormalized归一化...")
                    # 使用 ApkNormalized 预处理
                    normalized_cmd = [
                        "ApkNormalized",
                        str(source_apk),
                        str(normalized_apk),
                    ]
                    logging.info(f"执行ApkNormalized命令: {' '.join(normalized_cmd)}")
                    subprocess.run(
                        normalized_cmd,
                        stdout=sys.stdout,
                        stderr=sys.stderr,
                        text=True,
                        encoding="utf-8",  # ✅ 修改为 utf-8
                        errors="replace",  # ✅ 可选，避免报错，替换非法字符
                    )
                    logging.info(f"ApkNormalized命令执行完成，输出文件: {normalized_apk}，准备重新签名")
                    # 使用 34.0.0 的apksigner重新签名，注意重签名后文件的体积、md5都发生变化
                    client_publish_async("build", "构建任务:build", "开始产物签名...")
                    signed_apk, signed_size, signed_md5 = sign_apk(str(normalized_apk), sign_config, target_apk)
                    logging.info(f"重新签名APK文件: {signed_apk}，签名后文件体积: {signed_size} 字节")
                    is_normalized = True
                except Exception as e:
                    logging.error(f"AppNormalize\重新签名APK文件时发生错误: {e}")
                    is_normalized = False
                    # 回退到原始APK
                    shutil.copy2(source_apk, target_apk)
                    logging.info(f"回退复制APK文件: {apk_name}")
            else:
                logging.info("非 release 模式，无需 normalized")
                is_normalized = False
                # 回退到原始APK
                shutil.copy2(source_apk, target_apk)
                logging.info(f"回退复制APK文件: {apk_name}")
        else:
            logging.error(f"源APK文件不存在: {source_apk}")
            return False, ""

        # 复制metadata文件
        source_metadata = output_dir / "release-metadata.md"
        target_metadata = target_dir / "release-metadata.md"

        if source_metadata.exists():
            # 复制并修改metadata文件
            shutil.copy2(source_metadata, target_metadata)
            # 更新文件内容
            with open(target_metadata, "r+", encoding="utf-8") as f:
                content = f.read()
                # 提取MD5字段
                md5 = re.search(r"MD5: (\w+)", content).group(1)

                # 更新文件大小信息
                if is_normalized:
                    origin_md5 = re.search(r"MD5: (\w+)", content).group(1)
                    content = re.sub(r"MD5: \w+", f"MD5: {signed_md5}", content)
                    logging.info(f"原始 md5: {origin_md5}，修改后 md5: {signed_md5}")
                    md5 = signed_md5
                    origin_file_size = re.search(r"File Size: (\d+) bytes", content).group(1)
                    content = re.sub(
                        r"File Size: \d+ bytes \(\d+ KB\)",
                        f"File Size: {signed_size} bytes ({signed_size // 1024} KB)",
                        content,
                    )
                    logging.info(f"原始 file_size: {origin_file_size}，修改后 file_size: {signed_size}")

                # 添加额外信息
                content += f"\n\n打包请求: {config.last_commit_message}\n\nUniApp资源包是否混淆: {config.is_obfuscated} \n\n是否Normalized: {is_normalized}"

                # 重置文件指针并写入全部内容
                f.seek(0)
                f.write(content)
                f.truncate()

            # 创建MD5空白文件
            md5_path = target_dir / md5
            open(md5_path, "w").close()
            logging.info("成功复制并更新metadata文件")

            # 解析metadata并记录到服务器
            metadata = parse_metadata(content)
            logging.info(f"解析metadata文件结果: {json.dumps(metadata)}")
            record_task_metadata(metadata)

        else:
            logging.error(f"源metadata文件不存在: {source_metadata}")
            return False, ""

        return True, apk_name.replace(".apk", "")
    except Exception as e:
        logging.error(f"复制构建产物时发生错误: {e}")
        return False, ""


def record_task_metadata(metadata: BuildMetadata):
    """
    调用接口，记录任务对应的元数据
    """
    try:
        request_url = f"{config.SERVER_HOST_URL}/api/metadata/{config.cur_task_id}"
        response = requests.post(request_url, json=metadata)
        if response.status_code != 201:
            logging.error(f"调用接口提交元数据失败: {response.status_code} {response.text}")
            return False
        logging.info(f"调用接口提交元数据成功: {response.status_code} {response.text}")
        return True
    except Exception as e:
        logging.error(f"调用接口提交元数据失败: {e}")
        return False


# noinspection PyTypedDict
def parse_metadata(metadata_text: str) -> BuildMetadata:
    """
    解析metadata文件，从直观可读文件，解析出python风格的dict
    Args:
        metadata_text (str): 原始metadata文件内容
    Returns:
        BuildMetadata: 解析后的metadata info
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
        "是否Normalized": "is_normalized",
        "UniApp资源包是否混淆": "is_obfuscated",
        # "打包请求" intentionally omitted
    }

    # 转换为 dict 并跳过不需要的字段
    metadata: BuildMetadata = {}
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
                    # 提取后半段kb部分的数值
                    match = re.search(r"\d+ KB", value)
                    metadata[mapped_key] = int(match.group().replace(" KB", "")) if match else 0
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


def main(target_dir: Optional[Path] = None, release: bool = True, is_distribution: bool = True):
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
        sign_config = check_uni_base()

        # 执行gradle构建
        if not execute_gradle_build(release):
            logging.error("Gradle构建失败，终止执行")
            client_publish_async("build", "构建任务:build", "Gradle 构建失败")
            return 20001
        client_publish_async("build", "构建任务:build", "Gradle 构建完毕，开始生成产物...")
        # 获取从release目录读取构建产物名称
        apk_name = get_build_output_name(release)
        # 没有传递时，指向分发目录
        if target_dir is None:
            target_dir = get_distribution_target_dir(apk_name)

        # 复制构建产物，返回是否成功和apk文件名
        success, apk_name = copy_build_outputs(apk_name, target_dir, release, sign_config)
        if not success:
            logging.error("复制构建产物失败，终止执行")
            return 20002
        client_publish_async("build", "构建任务:build", "构建产物生成完毕，开始提交基座变更代码...")
        # 更新git信息，执行git add和git commit
        if is_distribution:
            # 来自分发的打包请求，附带提交打包请求的commit信息
            commit_message = f"release_req: {apk_name}{config.last_commit_message}"
        else:
            # 本地构建只记录变更时间
            commit_message = f"{'release' if release else 'debug'}: {datetime.now().strftime('%Y%m%d%H%M%S')}"

        if (git_code := update_git_info(commit_message)) != 0:
            logging.error("更新git信息失败，终止执行")
            return git_code

        logging.info("所有操作执行成功")
        client_publish_async("build", "构建任务:build", "构建完毕")
        return 0
    except Exception as e:
        logging.error(f"执行过程中发生错误: {e}")
        if isinstance(e, FileNotFoundError):
            return 12010
        return 1
    finally:
        # 清理
        git_reset_and_clean(repo_path=config.ANDROID_UNI_BASE_PATH)


def sign_apk(origin_apk: str, sign_config: SignConfig, output: str = None) -> tuple[str, int, str]:
    """
    对APK文件进行签名

    Args:
        origin_apk (str): 输入的原始文件路径字符串
        sign_config (SignConfig): 签名配置
        output (str, optional): 输出文件，如不配置则默认输出到.apk同目录下，文件名称为原文件名+_signed.apk

    Returns:
        str,int,str: 签名后的文件路径, 重新签名后的文件体积, 重签名后的文件md5
    """
    apk_signer = "/opt/android-sdk/build-tools/34.0.0/apksigner"
    if not os.path.exists(apk_signer):
        raise FileNotFoundError(f"apksigner 文件不存在: {apk_signer}")
    if output is None:
        output = os.path.splitext(origin_apk)[0] + "_signed.apk"
    cmd = [
        apk_signer,
        "sign",
        "--ks",
        str(sign_config.key_store),
        "--ks-key-alias",
        sign_config.alias,
        "--ks-pass",
        f"pass:{sign_config.ks_pass}",
        "--key-pass",
        f"pass:{sign_config.key_pass}",
        "--v1-signing-enabled",
        "true",
        "--v2-signing-enabled",
        "true",
        "--out",
        output,
        origin_apk,
    ]
    logging.info(f"执行命令: {' '.join(cmd)}")
    subprocess.run(
        cmd,
        stdout=sys.stdout,
        stderr=sys.stderr,
        text=True,
        encoding="utf-8",  # ✅ 修改为 utf-8
        errors="replace",  # ✅ 可选，避免报错，替换非法字符
    )
    # 检查输出目录下是否存在签名创建的idsig文件
    if os.path.exists(f"{output}.idsig"):
        # 删除idsig文件
        os.remove(f"{output}.idsig")
    # 获取重新签名后的文件体积\重新计算文件的md5
    return output, os.path.getsize(output), calculate_file_md5(output)


if __name__ == "__main__":
    main()
