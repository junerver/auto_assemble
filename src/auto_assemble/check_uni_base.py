import logging
import re
import shutil
from pathlib import Path
from typing import Optional

from common.api import fetch_project_info_by_prod_name, record_project_sign_config
from common.config import config
from common.types import SignConfig, ProjectConfig


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
        "项目目录": Path(config.ANDROID_UNI_BASE_PATH),
    }
    # 目录结构检查
    for name, path in paths_to_check.items():
        if not path.exists:
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
                item_path = path / item
                if not item_path.exists():
                    missing_items.append(item)

            if missing_items:
                error_msg = f"项目结构不完整，缺少以下必需项: {', '.join(missing_items)}"
                logging.error(error_msg)
                raise FileNotFoundError(error_msg)

            logging.info("项目结构检查通过")

    # 解析签名配置
    build_gradle_path = Path(config.ANDROID_UNI_BASE_PATH) / "app" / "build.gradle"
    if not build_gradle_path.exists():
        error_msg = f"app/build.gradle文件不存在: {build_gradle_path}"
        logging.error(error_msg)
        raise FileNotFoundError(error_msg)

    # 请求接口，检查是否存在有效的签名信息
    project_config: Optional[ProjectConfig] = fetch_project_info_by_prod_name(config.PROD_NAME)
    if project_config and project_config.is_sign_config_valid():
        # 签名有效
        return project_config.get_sign_config()
    else:
        # 提取 signingConfigs 区块内的 config 内容（非贪婪匹配）
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

            store_file_str: str = store_file_match.group(1)
            store_password = store_password_match.group(1)
            key_password = key_password_match.group(1)
            key_alias = key_alias_match.group(1)
            # 处理相对路径
            store_file = (Path(config.ANDROID_UNI_BASE_PATH) / "app" / store_file_str).resolve()
            # sign持久化路径，将签名文件保存在/app/sign目录下，并使用项目标识作为文件名前缀
            sign_path = config.SIGN_PATH
            sign_path.mkdir(parents=True, exist_ok=True)  # 确保目标目录存在
            key_store_file = sign_path / f"{config.PROD_NAME}_{store_file.name}"
            shutil.copy(store_file, key_store_file)

            sign_config = SignConfig(
                key_store=key_store_file,
                ks_pass=store_password,
                key_alias=key_alias,
                key_pass=key_password,
            )
            logging.info("签名配置解析成功")
            record_project_sign_config(project_config.id, sign_config)
            return sign_config

        except Exception as e:
            error_msg = f"解析签名配置失败: {str(e)}"
            logging.exception(error_msg)
            raise ValueError(error_msg)
