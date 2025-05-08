import logging
import os

from common.config import config


def check_uni_base():
    """
    检查基座工程目录是否存在，检查时需要检查项目是否符合Android基座工程结构，而不是一个空目录
    例如：目录中应该存在如下的目录、文件
        - app
        - gradle
        - build.gradle
        - setting.gradle
        - gradlew
        - gradlew.bat
    Raises:
        FileNotFoundError: 当基座工程目录不存在或项目结构不符合要求时抛出
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
                error_msg = (
                    f"项目结构不完整，缺少以下必需项: {', '.join(missing_items)}"
                )
                logging.error(error_msg)
                raise FileNotFoundError(error_msg)

            logging.info("项目结构检查通过")
