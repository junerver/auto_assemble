import logging
import os
import re

from common.config import config
from auto_assemble.types import SignConfig


def check_uni_base() -> SignConfig:
    """
    检查基座工程目录是否存在，检查时需要检查项目是否符合Android基座工程结构，而不是一个空目录
    例如：目录中应该存在如下的目录、文件
        - app
        - gradle
        - build.gradle
        - setting.gradle
        - gradlew
        - gradlew.bat
    同时解析app/build.gradle中的签名配置信息

    Returns:
        SignConfig: 签名配置信息

    Raises:
        FileNotFoundError: 当基座工程目录不存在或项目结构不符合要求时抛出
        ValueError: 当签名配置解析失败时抛出
    """
    paths_to_check = {
        "项目目录": config.ANDROID_UNI_BASE_PATH,
    }
    # 目录结构检查
    for name, path in paths_to_check.items():
        if not os.path.exists(path):
            error_msg = f"{name}不存在: {path}"
            logging.error(error_msg)
            raise FileNotFoundError(error_msg)
        else:
            # 检查Android项目必需的文件和目录
            required_items = [
                "app",
                "gradle",
                "build.gradle",
                "settings.gradle",
                "gradlew",
                "gradlew.bat",
            ]

            missing_items = []
            for item in required_items:
                item_path = os.path.join(path, item)
                if not os.path.exists(item_path):
                    missing_items.append(item)

            if missing_items:
                error_msg = f"项目结构不完整，缺少以下必需项: {', '.join(missing_items)}"
                logging.error(error_msg)
                raise FileNotFoundError(error_msg)

            logging.info("项目结构检查通过")

    # 解析签名配置
    build_gradle_path = os.path.join(config.ANDROID_UNI_BASE_PATH, "app", "build.gradle")
    if not os.path.exists(build_gradle_path):
        error_msg = f"app/build.gradle文件不存在: {build_gradle_path}"
        logging.error(error_msg)
        raise FileNotFoundError(error_msg)

    try:
        with open(build_gradle_path, "r", encoding="utf-8") as f:
            content = f.read()
        # 匹配 signingConfigs 区块内的 config 内容（非贪婪匹配）
        signing_block = re.search(r"signingConfigs\s*{([\s\S]*?)\n\s*}", content)
        if not signing_block:
            raise ValueError("未找到 signingConfigs 区块")

        config_block = signing_block.group(1)

        # 分别提取每个字段
        store_file_match = re.search(r"storeFile\s+file\(\s*'([^']+)'\s*\)", config_block)
        store_password_match = re.search(r"storePassword\s*'([^']+)'", config_block)
        key_password_match = re.search(r"keyPassword\s*'([^']+)'", config_block)
        key_alias_match = re.search(r"keyAlias\s*'([^']+)'", config_block)

        if not all([store_file_match, store_password_match, key_password_match, key_alias_match]):
            raise ValueError("解析签名配置失败: 未找到签名配置信息")

        store_file = store_file_match.group(1)
        store_password = store_password_match.group(1)
        key_password = key_password_match.group(1)
        key_alias = key_alias_match.group(1)
        # 处理相对路径
        if store_file.startswith(".."):
            store_file = os.path.abspath(os.path.join(config.ANDROID_UNI_BASE_PATH, "app", store_file))

        sign_config = SignConfig(
            alias=key_alias,
            ks_pass=store_password,
            key_pass=key_password,
            key_store=store_file,
        )

        logging.info("签名配置解析成功")
        return sign_config

    except Exception as e:
        error_msg = f"解析签名配置失败: {str(e)}"
        logging.error(error_msg)
        raise ValueError(error_msg)


if __name__ == "__main__":
    config._android_uni_base_path = r"D:\dev\project\uni-base"
    sign_config = check_uni_base()
    print(sign_config)
